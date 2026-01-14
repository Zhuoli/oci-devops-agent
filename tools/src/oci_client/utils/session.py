"""
Session management utilities for OCI authentication.
"""

import fcntl
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from rich.console import Console

try:
    import oci
except ImportError:
    oci = None

from ..client import OCIClient, create_oci_session_token
from .display import display_error, display_session_token_header, display_success, display_warning
from .yamler import get_tenancy_info_for_region_safe

console = Console()
logger = logging.getLogger(__name__)


@contextmanager
def oci_config_lock():
    """
    Context manager for locking OCI config file access.

    This prevents race conditions when multiple parallel requests
    try to create or validate session tokens simultaneously.
    """
    lock_file = Path.home() / ".oci" / ".config.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.touch(exist_ok=True)

    with open(lock_file, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def create_profile_for_region(
    project_name: str, stage: str, region: str, realm: Optional[str] = None
) -> str:
    """
    Generate profile name for a specific project, stage, realm, and region.

    The profile name includes the realm (oc1, oc17, etc.) to ensure
    different tenancies (e.g., dev vs prod in same region) get isolated profiles.
    """
    realm_part = realm if realm else "default"
    return f"{project_name}_{stage}_{realm_part}_{region.replace('-', '_')}"


def check_session_token_validity(
    profile_name: str,
    expected_region: Optional[str] = None,
    config_file_path: Optional[str] = None,
) -> bool:
    """
    Check if a session token for the given profile is still valid.

    Note: Tenancy validation is skipped because bmc_operator_access is a super-tenancy
    that can access all other tenancies, so the tenancy OCID in the profile won't match
    the target tenancy OCID in meta.yaml.

    Args:
        profile_name: Name of the OCI profile to check
        expected_region: Expected region the token should be for (validates region match)
        config_file_path: Optional path to OCI config file

    Returns:
        bool: True if session token exists, is valid, and matches expected region
    """
    logger.info(f"[SESSION_CHECK] Checking session token validity for profile '{profile_name}'")
    logger.info(f"[SESSION_CHECK] Expected region: {expected_region}")

    if not oci:
        logger.warning("[SESSION_CHECK] FAILED: OCI SDK not available")
        return False

    try:
        # Try to load the config for this profile
        config_path = config_file_path or str(Path.home() / ".oci" / "config")
        logger.info(f"[SESSION_CHECK] Config file path: {config_path}")

        if not Path(config_path).exists():
            logger.warning(f"[SESSION_CHECK] FAILED: Config file does not exist: {config_path}")
            return False

        # Try to load the profile configuration
        logger.info(f"[SESSION_CHECK] Loading profile '{profile_name}' from config...")
        try:
            config = oci.config.from_file(file_location=config_path, profile_name=profile_name)
            logger.info(f"[SESSION_CHECK] Profile '{profile_name}' loaded successfully")
        except Exception as profile_err:
            logger.warning(
                f"[SESSION_CHECK] FAILED: Could not load profile '{profile_name}': {profile_err}"
            )
            return False

        # Check if this is a session token profile (has security_token_file)
        if "security_token_file" not in config:
            logger.warning(
                f"[SESSION_CHECK] FAILED: Profile '{profile_name}' has no security_token_file"
            )
            return False

        token_file_path = Path(config["security_token_file"])
        logger.info(f"[SESSION_CHECK] Token file path: {token_file_path}")

        # Check if the token file exists
        if not token_file_path.exists():
            logger.warning(
                f"[SESSION_CHECK] FAILED: Token file does not exist: {token_file_path}"
            )
            return False

        # Check if the token file is not too old (session tokens typically expire after 1 hour)
        # We'll consider it valid if it's less than 50 minutes old to provide a buffer
        token_age_seconds = time.time() - token_file_path.stat().st_mtime
        token_age_minutes = token_age_seconds / 60
        max_age_seconds = 50 * 60  # 50 minutes

        logger.info(
            f"[SESSION_CHECK] Token age: {token_age_minutes:.1f} minutes "
            f"(max allowed: {max_age_seconds / 60} minutes)"
        )

        if token_age_seconds > max_age_seconds:
            logger.warning(
                f"[SESSION_CHECK] FAILED: Token too old - {token_age_minutes:.1f} minutes "
                f"(exceeds {max_age_seconds / 60} minute threshold)"
            )
            return False

        # Validate region matches if expected_region is provided
        if expected_region:
            profile_region = config.get("region", "")
            logger.info(
                f"[SESSION_CHECK] Region check - profile: '{profile_region}', "
                f"expected: '{expected_region}'"
            )
            if profile_region.lower() != expected_region.lower():
                logger.warning(
                    f"[SESSION_CHECK] FAILED: Region mismatch - "
                    f"profile has '{profile_region}', expected '{expected_region}'"
                )
                return False

        # Note: Tenancy validation is skipped - bmc_operator_access is a super-tenancy
        # that can access all other tenancies, so tenancy OCID won't match meta.yaml

        # Try to use the config to make a simple API call to verify it works
        # Session token profiles need a SecurityTokenSigner, not the default signer
        logger.info("[SESSION_CHECK] Validating token with API call to get_tenancy()...")
        try:
            # Read the token file to create a security token signer
            token_file = config["security_token_file"]
            with open(token_file, "r") as f:
                token = f.read().strip()

            private_key = oci.signer.load_private_key_from_file(config["key_file"])
            signer = oci.auth.signers.SecurityTokenSigner(token, private_key)

            identity_client = oci.identity.IdentityClient(config, signer=signer)
            # Make a simple API call to verify the token works
            tenancy_ocid = config["tenancy"]
            logger.info(f"[SESSION_CHECK] Calling get_tenancy({tenancy_ocid[:30]}...)")
            identity_client.get_tenancy(tenancy_ocid)
            logger.info("[SESSION_CHECK] SUCCESS: Token is valid and API call succeeded")
            return True
        except Exception as e:
            # If the API call fails, the token is probably expired or invalid
            logger.warning(
                f"[SESSION_CHECK] FAILED: API validation call failed - {type(e).__name__}: {e}"
            )
            return False

    except Exception as e:
        # If any step fails, assume the session token is not valid
        logger.warning(
            f"[SESSION_CHECK] FAILED: Unexpected error during validation - "
            f"{type(e).__name__}: {e}"
        )
        return False


def get_session_token_info(
    profile_name: str, config_file_path: Optional[str] = None
) -> Optional[dict]:
    """
    Get information about an existing session token.

    Returns:
        dict with token info or None if not found/invalid
    """
    if not oci:
        return None

    try:
        config_path = config_file_path or str(Path.home() / ".oci" / "config")
        if not Path(config_path).exists():
            return None

        config = oci.config.from_file(file_location=config_path, profile_name=profile_name)

        if "security_token_file" not in config:
            return None

        token_file_path = Path(config["security_token_file"])
        if not token_file_path.exists():
            return None

        token_age_seconds = time.time() - token_file_path.stat().st_mtime
        token_age_minutes = token_age_seconds / 60

        return {
            "profile_name": profile_name,
            "token_file": str(token_file_path),
            "age_minutes": token_age_minutes,
            "region": config.get("region", "unknown"),
            "tenancy": config.get("tenancy", "unknown"),
        }

    except Exception:
        return None


def setup_session_token(
    project_name: str, stage: str, region: str, config_file: str = "meta.yaml"
) -> str:
    """
    Create or reuse session token for a region and return the profile name to use.

    This function is thread-safe and handles concurrent access properly.
    It loads realm and tenancy information from meta.yaml to ensure proper isolation
    between different tenancies (e.g., dev vs prod in same region).

    Args:
        project_name: Project name from meta.yaml
        stage: Stage name (e.g., 'dev', 'staging', 'prod')
        region: OCI region name (e.g., 'us-phoenix-1')
        config_file: Path to meta.yaml config file

    Returns:
        str: Profile name to use (either the existing/created profile or fallback to DEFAULT)
    """
    logger.info(
        f"[SESSION_SETUP] ========== Starting session setup =========="
    )
    logger.info(
        f"[SESSION_SETUP] project={project_name}, stage={stage}, region={region}, "
        f"config_file={config_file}"
    )

    # Load tenancy info from meta.yaml to get realm (tenancy_ocid not validated since
    # bmc_operator_access is a super-tenancy that can access all other tenancies)
    _tenancy_ocid, _tenancy_name, realm = get_tenancy_info_for_region_safe(
        config_file, project_name, stage, region
    )
    logger.info(f"[SESSION_SETUP] Loaded from meta.yaml - realm: {realm}")

    if not realm:
        logger.warning(
            f"[SESSION_SETUP] No realm found in meta.yaml for {project_name}/{stage}/{region}. "
            "Using 'default' as realm."
        )
        realm = "default"

    # Generate profile name including realm for isolation
    target_profile = create_profile_for_region(project_name, stage, region, realm)
    logger.info(f"[SESSION_SETUP] Target profile name: '{target_profile}'")

    # Use file locking to prevent race conditions
    logger.info("[SESSION_SETUP] Acquiring config file lock...")
    with oci_config_lock():
        logger.info("[SESSION_SETUP] Lock acquired, checking for existing valid session...")

        # Check if we already have a valid session token for this profile
        # Note: Only region is validated, not tenancy (bmc_operator_access is cross-tenancy)
        if check_session_token_validity(
            target_profile,
            expected_region=region,
        ):
            token_info = get_session_token_info(target_profile)
            if token_info:
                age_minutes = token_info["age_minutes"]
                logger.info(
                    f"[SESSION_SETUP] REUSING existing session token "
                    f"(age: {age_minutes:.1f} minutes)"
                )
                display_success(
                    f"✓ Using existing valid session token for profile '{target_profile}' "
                    f"(age: {age_minutes:.1f} minutes, realm: {realm})"
                )
                return target_profile

        # If no valid session exists, create a new one
        logger.info(
            f"[SESSION_SETUP] No valid session found, will CREATE NEW session token"
        )
        display_session_token_header(target_profile)
        logger.info(f"[SESSION_SETUP] Creating new session token for realm '{realm}' in region '{region}'")

        try:
            # Create session token - always use bmc_operator_access as tenancy-name
            logger.info(
                f"[SESSION_SETUP] Calling create_oci_session_token("
                f"profile={target_profile}, region={region}, tenancy=bmc_operator_access)"
            )
            token_success = create_oci_session_token(
                profile_name=target_profile,
                region_name=region,
                tenancy_name="bmc_operator_access",
            )

            if not token_success:
                logger.error("[SESSION_SETUP] Token creation returned False, falling back to DEFAULT")
                display_error("Failed to create session token. Using DEFAULT profile...")
                return "DEFAULT"  # Fall back to DEFAULT profile

            logger.info(f"[SESSION_SETUP] Token created successfully, returning profile '{target_profile}'")
            return target_profile

        except Exception as e:
            logger.error(f"[SESSION_SETUP] Token creation failed with exception: {type(e).__name__}: {e}")
            display_warning(f"Could not create session token: {e}")
            display_warning("Falling back to DEFAULT profile...")
            return "DEFAULT"


def create_oci_client(region: str, profile_name: str) -> Optional[OCIClient]:
    """
    Create and initialize OCI client for a specific region.

    Returns:
        OCIClient or None if initialization fails
    """
    try:
        client = OCIClient(region=region, profile_name=profile_name)
        return client

    except Exception as e:
        display_error(f"Failed to initialize OCI client for region {region}: {e}")
        display_warning(f"Make sure you have configured OCI authentication for region {region}")
        return None


def display_connection_info(client: OCIClient) -> None:
    """Display connection and configuration information."""
    console.print("[bold blue]🔗 Connection Information[/bold blue]")

    # Test connection
    if client.test_connection():
        display_success("✓ Successfully connected to OCI")
    else:
        display_error("✗ Failed to connect to OCI")
        return

    # Display config info
    config_file = client.config.config_file or "~/.oci/config (default)"
    console.print(f"[dim]Config file: {config_file}[/dim]")
    console.print(f"[dim]Profile: {client.config.profile_name}[/dim]")
    console.print(f"[dim]Region: {client.config.region}[/dim]")

    # Display auth type
    if client.config.is_session_token_auth():
        console.print("[dim]Auth type: Session Token[/dim]")
    else:
        console.print("[dim]Auth type: API Key[/dim]")

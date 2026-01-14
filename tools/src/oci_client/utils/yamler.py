from typing import Any, Dict, Optional, Tuple

import yaml


class ConfigNotFoundError(Exception):
    """Custom exception for configuration not found errors."""

    pass


# Reserved keys at the realm level (not region names)
REALM_RESERVED_KEYS = {"tenancy-ocid", "tenancy-name"}


def get_compartment_id(
    yaml_file_path: str, project_name: str, stage: str, realm: str, region: str
) -> str:
    """
    Read a YAML configuration file and retrieve the compartment_id based on the provided parameters.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project (e.g., 'project-alpha', 'project-beta')
        stage: Deployment stage (e.g., 'dev', 'staging', 'prod')
        realm: Realm identifier (e.g., 'oc1', 'oc16', 'oc17')
        region: Region identifier (e.g., 'us-phoenix-1', 'us-ashburn-1')

    Returns:
        str: The compartment_id for the specified configuration

    Raises:
        ConfigNotFoundError: If the specified configuration path is not found
        FileNotFoundError: If the YAML file cannot be found
        yaml.YAMLError: If the YAML file is malformed
    """
    try:
        # Load the YAML file
        with open(yaml_file_path, "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found at path: {yaml_file_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")

    # Navigate through the configuration structure
    error_path = []

    # Check if 'projects' exists
    if "projects" not in config:
        raise ConfigNotFoundError("'projects' key not found in configuration")
    error_path.append("projects")

    # Check if project_name exists
    if project_name not in config["projects"]:
        available_projects = list(config["projects"].keys())
        raise ConfigNotFoundError(
            f"Project '{project_name}' not found. Available projects: {', '.join(available_projects)}"
        )
    error_path.append(project_name)

    # Check if stage exists
    if stage not in config["projects"][project_name]:
        available_stages = list(config["projects"][project_name].keys())
        raise ConfigNotFoundError(
            f"Stage '{stage}' not found for project '{project_name}'. "
            f"Available stages: {', '.join(available_stages)}"
        )
    error_path.append(stage)

    # Check if realm exists
    if realm not in config["projects"][project_name][stage]:
        available_realms = list(config["projects"][project_name][stage].keys())
        raise ConfigNotFoundError(
            f"Realm '{realm}' not found for path projects.{project_name}.{stage}. "
            f"Available realms: {', '.join(available_realms)}"
        )
    error_path.append(realm)

    # Check if region exists (excluding reserved keys like tenancy-ocid, tenancy-name)
    realm_config = config["projects"][project_name][stage][realm]
    if region not in realm_config or region in REALM_RESERVED_KEYS:
        available_regions = [k for k in realm_config.keys() if k not in REALM_RESERVED_KEYS]
        raise ConfigNotFoundError(
            f"Region '{region}' not found for path projects.{project_name}.{stage}.{realm}. "
            f"Available regions: {', '.join(available_regions)}"
        )
    error_path.append(region)

    # Check if compartment_id exists
    region_config = config["projects"][project_name][stage][realm][region]
    if not isinstance(region_config, dict) or "compartment_id" not in region_config:
        raise ConfigNotFoundError(
            f"'compartment_id' not found for path projects.{project_name}.{stage}.{realm}.{region}"
        )

    return str(region_config["compartment_id"])


def get_compartment_id_safe(
    yaml_file_path: str,
    project_name: str,
    stage: str,
    realm: str,
    region: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Safe version of get_compartment_id that returns a default value on error.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project
        stage: Deployment stage
        realm: Realm identifier
        region: Region identifier
        default: Default value to return if configuration is not found

    Returns:
        Optional[str]: The compartment_id or the default value if not found
    """
    try:
        return get_compartment_id(yaml_file_path, project_name, stage, realm, region)
    except (ConfigNotFoundError, FileNotFoundError, yaml.YAMLError):
        return default


def get_region_compartment_pairs(
    yaml_file_path: str, project_name: str, stage: str
) -> Dict[str, str]:
    """
    Get all region:compartment_id pairs for a given project and stage.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project (e.g., 'project-alpha', 'project-beta')
        stage: Deployment stage (e.g., 'dev', 'staging', 'prod')

    Returns:
        Dict[str, str]: Dictionary with region as key and compartment_id as value

    Raises:
        ConfigNotFoundError: If the specified project or stage is not found
        FileNotFoundError: If the YAML file cannot be found
        yaml.YAMLError: If the YAML file is malformed
    """
    try:
        # Load the YAML file
        with open(yaml_file_path, "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found at path: {yaml_file_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")

    # Check if 'projects' exists
    if "projects" not in config:
        raise ConfigNotFoundError("'projects' key not found in configuration")

    # Check if project_name exists
    if project_name not in config["projects"]:
        available_projects = list(config["projects"].keys())
        raise ConfigNotFoundError(
            f"Project '{project_name}' not found. Available projects: {', '.join(available_projects)}"
        )

    # Check if stage exists
    if stage not in config["projects"][project_name]:
        available_stages = list(config["projects"][project_name].keys())
        raise ConfigNotFoundError(
            f"Stage '{stage}' not found for project '{project_name}'. "
            f"Available stages: {', '.join(available_stages)}"
        )

    # Extract region:compartment_id pairs from all realms
    region_compartment_pairs = {}
    stage_config = config["projects"][project_name][stage]

    # Iterate through all realms (oc1, oc16, oc17, etc.)
    for realm, realm_config in stage_config.items():
        # Iterate through all regions in this realm (skip reserved keys like tenancy-ocid, tenancy-name)
        for region, region_config in realm_config.items():
            # Skip reserved keys (tenancy-ocid, tenancy-name)
            if region in REALM_RESERVED_KEYS:
                continue
            if isinstance(region_config, dict) and "compartment_id" in region_config:
                # Use region as key, compartment_id as value
                region_compartment_pairs[region] = region_config["compartment_id"]

    return region_compartment_pairs


def list_available_configs(yaml_file_path: str) -> Dict[str, Any]:
    """
    List all available configurations in the YAML file.

    Args:
        yaml_file_path: Path to the YAML configuration file

    Returns:
        Dict containing the structure of available configurations
    """
    try:
        with open(yaml_file_path, "r") as file:
            config = yaml.safe_load(file)

        from typing import List

        available: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
        if "projects" in config:
            for project, stages in config["projects"].items():
                available[project] = {}
                for stage, realms in stages.items():
                    available[project][stage] = {}
                    for realm, realm_config in realms.items():
                        # Filter out reserved keys (tenancy-ocid, tenancy-name)
                        regions = [k for k in realm_config.keys() if k not in REALM_RESERVED_KEYS]
                        available[project][stage][realm] = regions

        return available
    except Exception as e:
        return {"error": str(e)}


def get_tenancy_info(
    yaml_file_path: str, project_name: str, stage: str, realm: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get tenancy information (OCID and name) for a given project, stage, and realm.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project (e.g., 'project-alpha', 'project-beta')
        stage: Deployment stage (e.g., 'dev', 'staging', 'prod')
        realm: Realm identifier (e.g., 'oc1', 'oc16', 'oc17')

    Returns:
        Tuple[Optional[str], Optional[str]]: (tenancy_ocid, tenancy_name) or (None, None) if not found

    Raises:
        ConfigNotFoundError: If the specified configuration path is not found
        FileNotFoundError: If the YAML file cannot be found
        yaml.YAMLError: If the YAML file is malformed
    """
    try:
        with open(yaml_file_path, "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found at path: {yaml_file_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")

    # Check if 'projects' exists
    if "projects" not in config:
        raise ConfigNotFoundError("'projects' key not found in configuration")

    # Check if project_name exists
    if project_name not in config["projects"]:
        available_projects = list(config["projects"].keys())
        raise ConfigNotFoundError(
            f"Project '{project_name}' not found. Available projects: {', '.join(available_projects)}"
        )

    # Check if stage exists
    if stage not in config["projects"][project_name]:
        available_stages = list(config["projects"][project_name].keys())
        raise ConfigNotFoundError(
            f"Stage '{stage}' not found for project '{project_name}'. "
            f"Available stages: {', '.join(available_stages)}"
        )

    # Check if realm exists
    if realm not in config["projects"][project_name][stage]:
        available_realms = list(config["projects"][project_name][stage].keys())
        raise ConfigNotFoundError(
            f"Realm '{realm}' not found for path projects.{project_name}.{stage}. "
            f"Available realms: {', '.join(available_realms)}"
        )

    realm_config = config["projects"][project_name][stage][realm]
    tenancy_ocid = realm_config.get("tenancy-ocid")
    tenancy_name = realm_config.get("tenancy-name")

    return tenancy_ocid, tenancy_name


def get_tenancy_info_safe(
    yaml_file_path: str,
    project_name: str,
    stage: str,
    realm: str,
    default: Tuple[Optional[str], Optional[str]] = (None, None),
) -> Tuple[Optional[str], Optional[str]]:
    """
    Safe version of get_tenancy_info that returns a default value on error.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project
        stage: Deployment stage
        realm: Realm identifier
        default: Default value to return if configuration is not found

    Returns:
        Tuple[Optional[str], Optional[str]]: (tenancy_ocid, tenancy_name) or default if not found
    """
    try:
        return get_tenancy_info(yaml_file_path, project_name, stage, realm)
    except (ConfigNotFoundError, FileNotFoundError, yaml.YAMLError):
        return default


def get_all_tenancies(
    yaml_file_path: str, project_name: str, stage: str
) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """
    Get all tenancy information for a given project and stage across all realms.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project (e.g., 'project-alpha', 'project-beta')
        stage: Deployment stage (e.g., 'dev', 'staging', 'prod')

    Returns:
        Dict[str, Tuple[Optional[str], Optional[str]]]: Dictionary with realm as key
            and (tenancy_ocid, tenancy_name) tuple as value

    Raises:
        ConfigNotFoundError: If the specified project or stage is not found
        FileNotFoundError: If the YAML file cannot be found
        yaml.YAMLError: If the YAML file is malformed
    """
    try:
        with open(yaml_file_path, "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found at path: {yaml_file_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")

    # Check if 'projects' exists
    if "projects" not in config:
        raise ConfigNotFoundError("'projects' key not found in configuration")

    # Check if project_name exists
    if project_name not in config["projects"]:
        available_projects = list(config["projects"].keys())
        raise ConfigNotFoundError(
            f"Project '{project_name}' not found. Available projects: {', '.join(available_projects)}"
        )

    # Check if stage exists
    if stage not in config["projects"][project_name]:
        available_stages = list(config["projects"][project_name].keys())
        raise ConfigNotFoundError(
            f"Stage '{stage}' not found for project '{project_name}'. "
            f"Available stages: {', '.join(available_stages)}"
        )

    # Extract tenancy info from all realms
    tenancies: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    stage_config = config["projects"][project_name][stage]

    for realm, realm_config in stage_config.items():
        tenancy_ocid = realm_config.get("tenancy-ocid")
        tenancy_name = realm_config.get("tenancy-name")
        tenancies[realm] = (tenancy_ocid, tenancy_name)

    return tenancies


def get_tenancy_info_for_region(
    yaml_file_path: str, project_name: str, stage: str, region: str
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get tenancy information for a specific region by searching through all realms.

    This function finds which realm contains the given region and returns
    the tenancy info for that realm.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project (e.g., 'project-alpha', 'project-beta')
        stage: Deployment stage (e.g., 'dev', 'staging', 'prod')
        region: OCI region name (e.g., 'us-phoenix-1', 'us-ashburn-1')

    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]: (tenancy_ocid, tenancy_name, realm)
        or (None, None, None) if not found

    Raises:
        ConfigNotFoundError: If the specified project or stage is not found
        FileNotFoundError: If the YAML file cannot be found
        yaml.YAMLError: If the YAML file is malformed
    """
    try:
        with open(yaml_file_path, "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found at path: {yaml_file_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")

    # Check if 'projects' exists
    if "projects" not in config:
        raise ConfigNotFoundError("'projects' key not found in configuration")

    # Check if project_name exists
    if project_name not in config["projects"]:
        available_projects = list(config["projects"].keys())
        raise ConfigNotFoundError(
            f"Project '{project_name}' not found. Available projects: {', '.join(available_projects)}"
        )

    # Check if stage exists
    if stage not in config["projects"][project_name]:
        available_stages = list(config["projects"][project_name].keys())
        raise ConfigNotFoundError(
            f"Stage '{stage}' not found for project '{project_name}'. "
            f"Available stages: {', '.join(available_stages)}"
        )

    # Search through all realms to find the one containing this region
    stage_config = config["projects"][project_name][stage]

    for realm, realm_config in stage_config.items():
        # Check if the region exists in this realm (excluding reserved keys)
        for key in realm_config.keys():
            if key in REALM_RESERVED_KEYS:
                continue
            if key == region:
                tenancy_ocid = realm_config.get("tenancy-ocid")
                tenancy_name = realm_config.get("tenancy-name")
                return tenancy_ocid, tenancy_name, realm

    # Region not found in any realm
    raise ConfigNotFoundError(
        f"Region '{region}' not found for project '{project_name}' stage '{stage}'"
    )


def get_tenancy_info_for_region_safe(
    yaml_file_path: str,
    project_name: str,
    stage: str,
    region: str,
    default: Tuple[Optional[str], Optional[str], Optional[str]] = (None, None, None),
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Safe version of get_tenancy_info_for_region that returns a default value on error.

    Args:
        yaml_file_path: Path to the YAML configuration file
        project_name: Name of the project
        stage: Deployment stage
        region: OCI region name
        default: Default value to return if configuration is not found

    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]: (tenancy_ocid, tenancy_name, realm)
        or default if not found
    """
    try:
        return get_tenancy_info_for_region(yaml_file_path, project_name, stage, region)
    except (ConfigNotFoundError, FileNotFoundError, yaml.YAMLError):
        return default


# Example usage
if __name__ == "__main__":
    # Example 1: Get compartment_id with error handling
    try:
        compartment_id = get_compartment_id(
            yaml_file_path="meta.yaml",
            project_name="project-alpha",
            stage="dev",
            realm="oc1",
            region="us-phoenix-1",
        )
        print(f"Compartment ID: {compartment_id}")
    except ConfigNotFoundError as e:
        print(f"Configuration error: {e}")
    except FileNotFoundError as e:
        print(f"File error: {e}")
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {e}")

    # Example 2: Get compartment_id with safe version (returns None on error)
    safe_compartment_id: Optional[str] = get_compartment_id_safe(
        yaml_file_path="meta.yaml",
        project_name="project-beta",
        stage="prod",
        realm="oc1",
        region="us-phoenix-1",
        default="DEFAULT_COMPARTMENT_ID",
    )
    print(f"Safe Compartment ID: {safe_compartment_id}")

    # Example 3: List all available configurations
    available = list_available_configs("meta.yaml")
    print("\nAvailable configurations:")
    for project, stages in available.items():
        print(f"  Project: {project}")
        for stage, realms in stages.items():
            print(f"    Stage: {stage}")
            for realm, regions in realms.items():
                print(f"      Realm: {realm} -> Regions: {regions}")

    # Example 4: Get tenancy information
    try:
        tenancy_ocid, tenancy_name = get_tenancy_info(
            yaml_file_path="meta.yaml",
            project_name="project-alpha",
            stage="dev",
            realm="oc1",
        )
        print(f"\nTenancy OCID: {tenancy_ocid}")
        print(f"Tenancy Name: {tenancy_name}")
    except ConfigNotFoundError as e:
        print(f"Configuration error: {e}")

    # Example 5: Get all tenancies for a project/stage
    try:
        tenancies = get_all_tenancies(
            yaml_file_path="meta.yaml",
            project_name="project-alpha",
            stage="prod",
        )
        print("\nTenancies for project-alpha/prod:")
        for realm, (ocid, name) in tenancies.items():
            print(f"  Realm: {realm} -> OCID: {ocid}, Name: {name}")
    except ConfigNotFoundError as e:
        print(f"Configuration error: {e}")

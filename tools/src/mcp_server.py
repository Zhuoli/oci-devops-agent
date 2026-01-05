#!/usr/bin/env python3
"""
OKE Operations MCP Server

A Model Context Protocol (MCP) server that provides tools for Oracle Kubernetes Engine (OKE)
operational tasks including:
- Listing and inspecting OKE clusters
- Upgrading OKE cluster control planes
- Upgrading node pool Kubernetes versions
- Cycling node pools to apply new images

Usage:
    python -m mcp_server
    # or
    mcp run src/mcp_server.py
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from oci.container_engine.models import (
    NodePoolCyclingDetails,
    UpdateNodePoolDetails,
)
from oci import exceptions as oci_exceptions

from oci_client.client import OCIClient
from oci_client.models import OKEClusterInfo, OKENodePoolInfo
from oci_client.utils.config import load_region_compartments
from oci_client.utils.session import create_oci_client, setup_session_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("oke-operations")


def _serialize_cluster(cluster: OKEClusterInfo) -> Dict[str, Any]:
    """Serialize OKEClusterInfo to a JSON-serializable dict."""
    return {
        "cluster_id": cluster.cluster_id,
        "name": cluster.name,
        "kubernetes_version": cluster.kubernetes_version,
        "lifecycle_state": cluster.lifecycle_state,
        "compartment_id": cluster.compartment_id,
        "available_upgrades": cluster.available_upgrades,
        "node_pools": [_serialize_node_pool(np) for np in cluster.node_pools],
    }


def _serialize_node_pool(node_pool: OKENodePoolInfo) -> Dict[str, Any]:
    """Serialize OKENodePoolInfo to a JSON-serializable dict."""
    return {
        "node_pool_id": node_pool.node_pool_id,
        "name": node_pool.name,
        "kubernetes_version": node_pool.kubernetes_version,
        "lifecycle_state": node_pool.lifecycle_state,
    }


def _get_client(
    project: str,
    stage: str,
    region: str,
    config_file: str = "meta.yaml",
) -> tuple[Optional[OCIClient], Optional[str]]:
    """
    Initialize an OCI client for the given project/stage/region.

    Returns:
        Tuple of (client, error_message). If client is None, error_message describes the issue.
    """
    try:
        profile_name = setup_session_token(project, stage, region)
        client = create_oci_client(region, profile_name)
        if not client:
            return None, f"Failed to initialize OCI client for region {region}"
        return client, None
    except Exception as e:
        return None, f"Error initializing OCI client: {str(e)}"


def _get_compartment_id(
    project: str,
    stage: str,
    region: str,
    config_file: str = "meta.yaml",
) -> Optional[str]:
    """Get compartment ID from meta.yaml configuration."""
    try:
        region_compartments = load_region_compartments(project, stage, config_file)
        return region_compartments.get(region)
    except Exception as e:
        logger.error(f"Failed to load compartment configuration: {e}")
        return None


@server.list_tools()
async def list_tools() -> List[Tool]:
    """Return the list of available tools."""
    return [
        Tool(
            name="list_oke_clusters",
            description="List all OKE clusters for a project, stage, and region. Returns cluster names, versions, and available upgrades.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name (e.g., 'project-alpha', 'project-beta')",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage name (e.g., 'dev', 'staging', 'prod')",
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region name (e.g., 'us-phoenix-1', 'us-ashburn-1')",
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file (default: meta.yaml)",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region"],
            },
        ),
        Tool(
            name="get_oke_cluster_details",
            description="Get detailed information about a specific OKE cluster including node pools and available upgrades.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage name",
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region name",
                    },
                    "cluster_id": {
                        "type": "string",
                        "description": "OKE cluster OCID",
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file (default: meta.yaml)",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region", "cluster_id"],
            },
        ),
        Tool(
            name="upgrade_oke_cluster",
            description="Upgrade an OKE cluster control plane to a target Kubernetes version. This initiates the upgrade and returns a work request ID for tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage name",
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region name",
                    },
                    "cluster_id": {
                        "type": "string",
                        "description": "OKE cluster OCID",
                    },
                    "target_version": {
                        "type": "string",
                        "description": "Target Kubernetes version (e.g., '1.34.1'). If not specified, upgrades to latest available.",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, only show what would be done without making changes",
                        "default": False,
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region", "cluster_id"],
            },
        ),
        Tool(
            name="list_node_pools",
            description="List all node pools for an OKE cluster with their current Kubernetes versions and states.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage name",
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region name",
                    },
                    "cluster_id": {
                        "type": "string",
                        "description": "OKE cluster OCID",
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region", "cluster_id"],
            },
        ),
        Tool(
            name="upgrade_node_pool",
            description="Upgrade an OKE node pool to a target Kubernetes version. This updates the node pool configuration; existing nodes need to be cycled to pick up the new version.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage name",
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region name",
                    },
                    "node_pool_id": {
                        "type": "string",
                        "description": "OKE node pool OCID",
                    },
                    "target_version": {
                        "type": "string",
                        "description": "Target Kubernetes version (e.g., '1.34.1')",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, only show what would be done without making changes",
                        "default": False,
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region", "node_pool_id", "target_version"],
            },
        ),
        Tool(
            name="cycle_node_pool",
            description="Cycle OKE node pool workers by replacing their boot volumes. This is used to apply new images or Kubernetes versions to existing worker nodes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage name",
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region name",
                    },
                    "node_pool_id": {
                        "type": "string",
                        "description": "OKE node pool OCID",
                    },
                    "maximum_unavailable": {
                        "type": "integer",
                        "description": "Maximum number of nodes that can be unavailable during cycling (default: 1)",
                        "default": 1,
                    },
                    "maximum_surge": {
                        "type": "integer",
                        "description": "Maximum number of additional nodes that can be created during cycling",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, only show what would be done without making changes",
                        "default": False,
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region", "node_pool_id"],
            },
        ),
        Tool(
            name="get_oke_version_report",
            description="Generate a version report for all OKE clusters in a project/stage, showing current versions and available upgrades.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Stage name",
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "list_oke_clusters":
            return await _list_oke_clusters(arguments)
        elif name == "get_oke_cluster_details":
            return await _get_oke_cluster_details(arguments)
        elif name == "upgrade_oke_cluster":
            return await _upgrade_oke_cluster(arguments)
        elif name == "list_node_pools":
            return await _list_node_pools(arguments)
        elif name == "upgrade_node_pool":
            return await _upgrade_node_pool(arguments)
        elif name == "cycle_node_pool":
            return await _cycle_node_pool(arguments)
        elif name == "get_oke_version_report":
            return await _get_oke_version_report(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.exception(f"Error executing tool {name}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _list_oke_clusters(arguments: Dict[str, Any]) -> List[TextContent]:
    """List OKE clusters for a project/stage/region."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    compartment_id = _get_compartment_id(project, stage, region, config_file)
    if not compartment_id:
        return [TextContent(type="text", text=f"Error: Could not find compartment ID for {project}/{stage}/{region}")]

    try:
        clusters = client.list_oke_clusters(compartment_id)
        result = {
            "project": project,
            "stage": stage,
            "region": region,
            "compartment_id": compartment_id,
            "cluster_count": len(clusters),
            "clusters": [_serialize_cluster(c) for c in clusters],
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing clusters: {str(e)}")]


async def _get_oke_cluster_details(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get detailed information about a specific OKE cluster."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    cluster_id = arguments["cluster_id"]
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    compartment_id = _get_compartment_id(project, stage, region, config_file)

    try:
        # Get cluster details
        cluster = client.get_oke_cluster(cluster_id)

        # Get node pools
        node_pools = client.list_node_pools(cluster_id, compartment_id)
        cluster.node_pools = node_pools

        result = {
            "project": project,
            "stage": stage,
            "region": region,
            "cluster": _serialize_cluster(cluster),
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting cluster details: {str(e)}")]


async def _upgrade_oke_cluster(arguments: Dict[str, Any]) -> List[TextContent]:
    """Upgrade an OKE cluster control plane."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    cluster_id = arguments["cluster_id"]
    target_version = arguments.get("target_version")
    dry_run = arguments.get("dry_run", False)
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    try:
        # Get current cluster state
        cluster = client.get_oke_cluster(cluster_id)

        # Determine target version
        if not target_version:
            if not cluster.available_upgrades:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "no_upgrade_needed",
                        "cluster_id": cluster_id,
                        "cluster_name": cluster.name,
                        "current_version": cluster.kubernetes_version,
                        "message": "No upgrades available for this cluster",
                    }, indent=2)
                )]
            # Use the latest available upgrade
            target_version = max(cluster.available_upgrades)

        # Validate target version is available
        if target_version not in cluster.available_upgrades:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "error",
                    "message": f"Target version {target_version} is not available",
                    "available_upgrades": cluster.available_upgrades,
                }, indent=2)
            )]

        if dry_run:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "dry_run",
                    "cluster_id": cluster_id,
                    "cluster_name": cluster.name,
                    "current_version": cluster.kubernetes_version,
                    "target_version": target_version,
                    "message": f"Would upgrade cluster from {cluster.kubernetes_version} to {target_version}",
                }, indent=2)
            )]

        # Perform the upgrade
        work_request_id = client.upgrade_oke_cluster(cluster_id, target_version)

        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "initiated",
                "cluster_id": cluster_id,
                "cluster_name": cluster.name,
                "current_version": cluster.kubernetes_version,
                "target_version": target_version,
                "work_request_id": work_request_id,
                "message": f"Cluster upgrade initiated. Track progress with work request: {work_request_id}",
            }, indent=2)
        )]
    except Exception as e:
        return [TextContent(type="text", text=f"Error upgrading cluster: {str(e)}")]


async def _list_node_pools(arguments: Dict[str, Any]) -> List[TextContent]:
    """List node pools for a cluster."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    cluster_id = arguments["cluster_id"]
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    compartment_id = _get_compartment_id(project, stage, region, config_file)

    try:
        node_pools = client.list_node_pools(cluster_id, compartment_id)
        result = {
            "cluster_id": cluster_id,
            "node_pool_count": len(node_pools),
            "node_pools": [_serialize_node_pool(np) for np in node_pools],
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing node pools: {str(e)}")]


async def _upgrade_node_pool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Upgrade a node pool to a target version."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    node_pool_id = arguments["node_pool_id"]
    target_version = arguments["target_version"]
    dry_run = arguments.get("dry_run", False)
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    try:
        if dry_run:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "dry_run",
                    "node_pool_id": node_pool_id,
                    "target_version": target_version,
                    "message": f"Would upgrade node pool to {target_version}",
                }, indent=2)
            )]

        # Perform the upgrade
        work_request_id = client.upgrade_oke_node_pool(node_pool_id, target_version)

        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "initiated",
                "node_pool_id": node_pool_id,
                "target_version": target_version,
                "work_request_id": work_request_id,
                "message": f"Node pool upgrade initiated. Note: Existing nodes need to be cycled to pick up the new version.",
            }, indent=2)
        )]
    except Exception as e:
        return [TextContent(type="text", text=f"Error upgrading node pool: {str(e)}")]


async def _cycle_node_pool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Cycle node pool workers to apply new images."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    node_pool_id = arguments["node_pool_id"]
    maximum_unavailable = arguments.get("maximum_unavailable", 1)
    maximum_surge = arguments.get("maximum_surge")
    dry_run = arguments.get("dry_run", False)
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    try:
        ce_client = client.container_engine_client

        # Get current node pool details
        node_pool_details = ce_client.get_node_pool(node_pool_id).data
        node_pool_name = getattr(node_pool_details, "name", node_pool_id)
        current_version = getattr(node_pool_details, "kubernetes_version", "unknown")
        nodes = getattr(node_pool_details, "nodes", []) or []

        if dry_run:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "dry_run",
                    "node_pool_id": node_pool_id,
                    "node_pool_name": node_pool_name,
                    "current_version": current_version,
                    "node_count": len(nodes),
                    "maximum_unavailable": maximum_unavailable,
                    "maximum_surge": maximum_surge,
                    "message": f"Would cycle {len(nodes)} node(s) in pool '{node_pool_name}' using boot volume replacement",
                }, indent=2)
            )]

        # Create cycling configuration
        cycling_details = NodePoolCyclingDetails(
            is_node_cycling_enabled=True,
            cycle_modes=["BOOT_VOLUME_REPLACE"],
            maximum_unavailable=str(maximum_unavailable),
            maximum_surge=str(maximum_surge) if maximum_surge is not None else None,
        )

        update_details = UpdateNodePoolDetails(
            kubernetes_version=current_version,
            node_pool_cycling_details=cycling_details,
        )

        # Initiate the cycle
        response = ce_client.update_node_pool(node_pool_id, update_details)
        work_request_id = response.headers.get("opc-work-request-id")

        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "initiated",
                "node_pool_id": node_pool_id,
                "node_pool_name": node_pool_name,
                "node_count": len(nodes),
                "maximum_unavailable": maximum_unavailable,
                "maximum_surge": maximum_surge,
                "work_request_id": work_request_id,
                "message": f"Node pool cycling initiated. Nodes will be replaced with boot volume replacement.",
            }, indent=2)
        )]
    except oci_exceptions.ServiceError as e:
        return [TextContent(type="text", text=f"OCI Service Error: {e.message}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error cycling node pool: {str(e)}")]


async def _get_oke_version_report(arguments: Dict[str, Any]) -> List[TextContent]:
    """Generate a version report for all OKE clusters in a project/stage."""
    project = arguments["project"]
    stage = arguments["stage"]
    config_file = arguments.get("config_file", "meta.yaml")

    try:
        region_compartments = load_region_compartments(project, stage, config_file)
    except Exception as e:
        return [TextContent(type="text", text=f"Error loading configuration: {str(e)}")]

    report = {
        "project": project,
        "stage": stage,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "regions": {},
        "summary": {
            "total_clusters": 0,
            "clusters_needing_upgrade": 0,
            "total_node_pools": 0,
        },
    }

    for region, compartment_id in region_compartments.items():
        client, error = _get_client(project, stage, region, config_file)
        if error:
            report["regions"][region] = {"error": error}
            continue

        try:
            clusters = client.list_oke_clusters(compartment_id)
            region_data = {
                "compartment_id": compartment_id,
                "cluster_count": len(clusters),
                "clusters": [],
            }

            for cluster in clusters:
                # Get node pools
                try:
                    node_pools = client.list_node_pools(cluster.cluster_id, compartment_id)
                except Exception:
                    node_pools = []

                cluster_data = {
                    "cluster_id": cluster.cluster_id,
                    "name": cluster.name,
                    "kubernetes_version": cluster.kubernetes_version,
                    "lifecycle_state": cluster.lifecycle_state,
                    "available_upgrades": cluster.available_upgrades,
                    "needs_upgrade": len(cluster.available_upgrades) > 0,
                    "node_pools": [_serialize_node_pool(np) for np in node_pools],
                }
                region_data["clusters"].append(cluster_data)

                # Update summary
                report["summary"]["total_clusters"] += 1
                report["summary"]["total_node_pools"] += len(node_pools)
                if cluster.available_upgrades:
                    report["summary"]["clusters_needing_upgrade"] += 1

            report["regions"][region] = region_data

        except Exception as e:
            report["regions"][region] = {"error": str(e)}

    return [TextContent(type="text", text=json.dumps(report, indent=2))]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

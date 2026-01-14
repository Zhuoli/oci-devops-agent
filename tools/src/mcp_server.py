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
import sys
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Configure logging to file for debugging
log_file = Path.cwd() / "mcp_server.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)
logger.info(f"MCP Server starting, log file: {log_file}")

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
    from oci import exceptions as oci_exceptions
    from oci.container_engine.models import NodePoolCyclingDetails, UpdateNodePoolDetails

    from oci_client.client import OCIClient
    from oci_client.models import (
        DeploymentInfo,
        DeploymentPipelineInfo,
        DevOpsProjectInfo,
        OKEClusterInfo,
        OKENodePoolInfo,
    )
    from oci_client.utils.config import load_region_compartments
    from oci_client.utils.session import create_oci_client, setup_session_token
    logger.info("All imports successful")
except Exception as e:
    logger.error(f"Import error: {e}")
    logger.error(traceback.format_exc())
    raise

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


def _serialize_devops_project(project: DevOpsProjectInfo) -> Dict[str, Any]:
    """Serialize DevOpsProjectInfo to a JSON-serializable dict."""
    return {
        "project_id": project.project_id,
        "name": project.name,
        "description": project.description,
        "compartment_id": project.compartment_id,
        "lifecycle_state": project.lifecycle_state,
        "time_created": project.time_created,
        "notification_config": project.notification_config,
    }


def _serialize_deployment_pipeline(pipeline: DeploymentPipelineInfo) -> Dict[str, Any]:
    """Serialize DeploymentPipelineInfo to a JSON-serializable dict."""
    return {
        "pipeline_id": pipeline.pipeline_id,
        "display_name": pipeline.display_name,
        "project_id": pipeline.project_id,
        "compartment_id": pipeline.compartment_id,
        "description": pipeline.description,
        "lifecycle_state": pipeline.lifecycle_state,
        "time_created": pipeline.time_created,
        "time_updated": pipeline.time_updated,
    }


def _serialize_deployment(deployment: DeploymentInfo) -> Dict[str, Any]:
    """Serialize DeploymentInfo to a JSON-serializable dict."""
    return {
        "deployment_id": deployment.deployment_id,
        "display_name": deployment.display_name,
        "deployment_type": deployment.deployment_type,
        "deploy_pipeline_id": deployment.deploy_pipeline_id,
        "compartment_id": deployment.compartment_id,
        "lifecycle_state": deployment.lifecycle_state,
        "lifecycle_details": deployment.lifecycle_details,
        "time_created": deployment.time_created,
        "time_started": deployment.time_started,
        "time_finished": deployment.time_finished,
        "deployment_execution_progress": deployment.deployment_execution_progress,
        "deployment_arguments": deployment.deployment_arguments,
        "freeform_tags": deployment.freeform_tags,
        "defined_tags": deployment.defined_tags,
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
        profile_name = setup_session_token(project, stage, region, config_file=config_file)
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
        Tool(
            name="list_cluster_nodes",
            description="List all worker nodes (compute instances) for an OKE cluster. Returns node details including lifecycle state, private IP, and node pool membership.",
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
            name="get_node_pool_details",
            description="Get detailed information about a specific node pool including all individual worker nodes and their states.",
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
            name="check_node_image_updates",
            description="Check which nodes in a cluster or compartment have newer OS images available. Compares current node images against the latest available images of the same type.",
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
                        "description": "OKE cluster OCID (optional - if not provided, checks all instances in compartment)",
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region"],
            },
        ),
        # ========== DevOps Tools ==========
        Tool(
            name="list_devops_projects",
            description="List all DevOps projects in a compartment. Returns project names, IDs, descriptions, and lifecycle states.",
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
            name="list_deployment_pipelines",
            description="List all deployment pipelines in a DevOps project or compartment. Returns pipeline names, IDs, and lifecycle states.",
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
                    "devops_project_id": {
                        "type": "string",
                        "description": "DevOps project OCID (optional - if not provided, lists all pipelines in compartment)",
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region"],
            },
        ),
        Tool(
            name="get_recent_deployment",
            description="Get the most recent deployment for a deployment pipeline. Returns deployment status (SUCCEEDED/FAILED/IN_PROGRESS), start time, finish time, and execution details including any errors.",
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
                    "pipeline_id": {
                        "type": "string",
                        "description": "Deployment pipeline OCID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent deployments to retrieve (default: 1)",
                        "default": 1,
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region", "pipeline_id"],
            },
        ),
        Tool(
            name="get_deployment_logs",
            description="Get detailed logs and error information for a specific deployment. Shows stage-by-stage execution details and highlights any failures with error messages.",
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
                    "deployment_id": {
                        "type": "string",
                        "description": "Deployment OCID",
                    },
                    "config_file": {
                        "type": "string",
                        "description": "Path to meta.yaml config file",
                        "default": "meta.yaml",
                    },
                },
                "required": ["project", "stage", "region", "deployment_id"],
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
        elif name == "list_cluster_nodes":
            return await _list_cluster_nodes(arguments)
        elif name == "get_node_pool_details":
            return await _get_node_pool_details(arguments)
        elif name == "check_node_image_updates":
            return await _check_node_image_updates(arguments)
        # DevOps tools
        elif name == "list_devops_projects":
            return await _list_devops_projects(arguments)
        elif name == "list_deployment_pipelines":
            return await _list_deployment_pipelines(arguments)
        elif name == "get_recent_deployment":
            return await _get_recent_deployment(arguments)
        elif name == "get_deployment_logs":
            return await _get_deployment_logs(arguments)
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
        return [
            TextContent(
                type="text",
                text=f"Error: Could not find compartment ID for {project}/{stage}/{region}",
            )
        ]

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
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "status": "no_upgrade_needed",
                                "cluster_id": cluster_id,
                                "cluster_name": cluster.name,
                                "current_version": cluster.kubernetes_version,
                                "message": "No upgrades available for this cluster",
                            },
                            indent=2,
                        ),
                    )
                ]
            # Use the latest available upgrade
            target_version = max(cluster.available_upgrades)

        # Validate target version is available
        if target_version not in cluster.available_upgrades:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "error",
                            "message": f"Target version {target_version} is not available",
                            "available_upgrades": cluster.available_upgrades,
                        },
                        indent=2,
                    ),
                )
            ]

        if dry_run:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "dry_run",
                            "cluster_id": cluster_id,
                            "cluster_name": cluster.name,
                            "current_version": cluster.kubernetes_version,
                            "target_version": target_version,
                            "message": f"Would upgrade cluster from {cluster.kubernetes_version} to {target_version}",
                        },
                        indent=2,
                    ),
                )
            ]

        # Perform the upgrade
        work_request_id = client.upgrade_oke_cluster(cluster_id, target_version)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "initiated",
                        "cluster_id": cluster_id,
                        "cluster_name": cluster.name,
                        "current_version": cluster.kubernetes_version,
                        "target_version": target_version,
                        "work_request_id": work_request_id,
                        "message": f"Cluster upgrade initiated. Track progress with work request: {work_request_id}",
                    },
                    indent=2,
                ),
            )
        ]
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
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "dry_run",
                            "node_pool_id": node_pool_id,
                            "target_version": target_version,
                            "message": f"Would upgrade node pool to {target_version}",
                        },
                        indent=2,
                    ),
                )
            ]

        # Perform the upgrade
        work_request_id = client.upgrade_oke_node_pool(node_pool_id, target_version)

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "initiated",
                        "node_pool_id": node_pool_id,
                        "target_version": target_version,
                        "work_request_id": work_request_id,
                        "message": f"Node pool upgrade initiated. Note: Existing nodes need to be cycled to pick up the new version.",
                    },
                    indent=2,
                ),
            )
        ]
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
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "dry_run",
                            "node_pool_id": node_pool_id,
                            "node_pool_name": node_pool_name,
                            "current_version": current_version,
                            "node_count": len(nodes),
                            "maximum_unavailable": maximum_unavailable,
                            "maximum_surge": maximum_surge,
                            "message": f"Would cycle {len(nodes)} node(s) in pool '{node_pool_name}' using boot volume replacement",
                        },
                        indent=2,
                    ),
                )
            ]

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

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "initiated",
                        "node_pool_id": node_pool_id,
                        "node_pool_name": node_pool_name,
                        "node_count": len(nodes),
                        "maximum_unavailable": maximum_unavailable,
                        "maximum_surge": maximum_surge,
                        "work_request_id": work_request_id,
                        "message": f"Node pool cycling initiated. Nodes will be replaced with boot volume replacement.",
                    },
                    indent=2,
                ),
            )
        ]
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


def _serialize_node(node: Any) -> Dict[str, Any]:
    """Serialize a node object to a JSON-serializable dict."""
    return {
        "node_id": getattr(node, "id", None),
        "name": getattr(node, "name", None),
        "lifecycle_state": getattr(node, "lifecycle_state", None),
        "private_ip": getattr(node, "private_ip", None),
        "public_ip": getattr(node, "public_ip", None),
        "availability_domain": getattr(node, "availability_domain", None),
        "fault_domain": getattr(node, "fault_domain", None),
        "subnet_id": getattr(node, "subnet_id", None),
        "node_pool_id": getattr(node, "node_pool_id", None),
        "kubernetes_version": getattr(node, "kubernetes_version", None),
        "node_error": _serialize_node_error(getattr(node, "node_error", None)),
    }


def _serialize_node_error(node_error: Any) -> Optional[Dict[str, Any]]:
    """Serialize node error information if present."""
    if node_error is None:
        return None
    return {
        "code": getattr(node_error, "code", None),
        "message": getattr(node_error, "message", None),
        "status": getattr(node_error, "status", None),
    }


async def _list_cluster_nodes(arguments: Dict[str, Any]) -> List[TextContent]:
    """List all worker nodes for an OKE cluster."""
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
        ce_client = client.container_engine_client

        # Get cluster name for context
        cluster = client.get_oke_cluster(cluster_id)

        # Get all node pools for the cluster
        node_pools = client.list_node_pools(cluster_id, compartment_id)

        all_nodes = []
        nodes_by_state = {}
        unhealthy_nodes = []

        for np in node_pools:
            # Get detailed node pool info including nodes
            try:
                np_details = ce_client.get_node_pool(np.node_pool_id).data
                nodes = getattr(np_details, "nodes", []) or []

                for node in nodes:
                    node_data = _serialize_node(node)
                    node_data["node_pool_name"] = np.name
                    all_nodes.append(node_data)

                    # Track state distribution
                    state = node_data.get("lifecycle_state", "UNKNOWN")
                    nodes_by_state[state] = nodes_by_state.get(state, 0) + 1

                    # Track unhealthy nodes (not ACTIVE)
                    if state not in ("ACTIVE", "CREATING"):
                        unhealthy_nodes.append(
                            {
                                "node_id": node_data.get("node_id"),
                                "name": node_data.get("name"),
                                "lifecycle_state": state,
                                "node_pool_name": np.name,
                                "node_error": node_data.get("node_error"),
                            }
                        )

            except Exception as e:
                logger.warning(f"Failed to get nodes for node pool {np.node_pool_id}: {e}")

        result = {
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "region": region,
            "total_nodes": len(all_nodes),
            "nodes_by_state": nodes_by_state,
            "unhealthy_node_count": len(unhealthy_nodes),
            "unhealthy_nodes": unhealthy_nodes,
            "nodes": all_nodes,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error listing cluster nodes: {str(e)}")]


async def _get_node_pool_details(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get detailed information about a specific node pool including all nodes."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    node_pool_id = arguments["node_pool_id"]
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    try:
        ce_client = client.container_engine_client

        # Get full node pool details
        np_details = ce_client.get_node_pool(node_pool_id).data
        nodes = getattr(np_details, "nodes", []) or []

        # Serialize all nodes
        serialized_nodes = [_serialize_node(node) for node in nodes]

        # Calculate state distribution
        nodes_by_state = {}
        unhealthy_nodes = []
        for node_data in serialized_nodes:
            state = node_data.get("lifecycle_state", "UNKNOWN")
            nodes_by_state[state] = nodes_by_state.get(state, 0) + 1

            if state not in ("ACTIVE", "CREATING"):
                unhealthy_nodes.append(
                    {
                        "node_id": node_data.get("node_id"),
                        "name": node_data.get("name"),
                        "lifecycle_state": state,
                        "node_error": node_data.get("node_error"),
                    }
                )

        # Get node source info (image details)
        node_source = getattr(np_details, "node_source", None)
        node_source_info = None
        if node_source:
            node_source_info = {
                "source_type": getattr(node_source, "source_type", None),
                "image_id": getattr(node_source, "image_id", None),
            }

        result = {
            "node_pool_id": node_pool_id,
            "name": getattr(np_details, "name", None),
            "cluster_id": getattr(np_details, "cluster_id", None),
            "compartment_id": getattr(np_details, "compartment_id", None),
            "kubernetes_version": getattr(np_details, "kubernetes_version", None),
            "lifecycle_state": getattr(np_details, "lifecycle_state", None),
            "node_shape": getattr(np_details, "node_shape", None),
            "node_source": node_source_info,
            "total_nodes": len(serialized_nodes),
            "nodes_by_state": nodes_by_state,
            "unhealthy_node_count": len(unhealthy_nodes),
            "unhealthy_nodes": unhealthy_nodes,
            "nodes": serialized_nodes,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except oci_exceptions.ServiceError as e:
        return [TextContent(type="text", text=f"OCI Service Error: {e.message}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting node pool details: {str(e)}")]


async def _check_node_image_updates(arguments: Dict[str, Any]) -> List[TextContent]:
    """Check which nodes have newer OS images available."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    cluster_id = arguments.get("cluster_id")  # Optional
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    compartment_id = _get_compartment_id(project, stage, region, config_file)
    if not compartment_id:
        return [
            TextContent(
                type="text",
                text=f"Error: Could not find compartment ID for {project}/{stage}/{region}",
            )
        ]

    try:
        compute_client = client.compute_client
        ce_client = client.container_engine_client

        # Collect nodes to check
        nodes_to_check = []

        if cluster_id:
            # Get nodes for specific cluster
            cluster = client.get_oke_cluster(cluster_id)
            node_pools = client.list_node_pools(cluster_id, compartment_id)

            for np in node_pools:
                try:
                    np_details = ce_client.get_node_pool(np.node_pool_id).data
                    node_source = getattr(np_details, "node_source", None)
                    pool_image_id = getattr(node_source, "image_id", None) if node_source else None

                    nodes = getattr(np_details, "nodes", []) or []
                    for node in nodes:
                        node_id = getattr(node, "id", None)
                        if node_id and getattr(node, "lifecycle_state", None) == "ACTIVE":
                            nodes_to_check.append(
                                {
                                    "node_id": node_id,
                                    "node_name": getattr(node, "name", node_id),
                                    "node_pool_id": np.node_pool_id,
                                    "node_pool_name": np.name,
                                    "pool_image_id": pool_image_id,
                                    "cluster_id": cluster_id,
                                    "cluster_name": cluster.name,
                                }
                            )
                except Exception as e:
                    logger.warning(f"Failed to get nodes for node pool {np.node_pool_id}: {e}")
        else:
            # Get all running instances in compartment and detect OKE nodes
            instances = client.list_oke_instances(compartment_id)
            for inst in instances:
                nodes_to_check.append(
                    {
                        "node_id": inst.instance_id,
                        "node_name": inst.display_name,
                        "node_pool_id": None,
                        "node_pool_name": None,
                        "pool_image_id": None,
                        "cluster_id": None,
                        "cluster_name": inst.cluster_name,
                    }
                )

        # Check each node for image updates
        results = []
        nodes_needing_update = 0
        nodes_up_to_date = 0
        nodes_unknown = 0

        for node_info in nodes_to_check:
            node_result = {
                "node_id": node_info["node_id"],
                "node_name": node_info["node_name"],
                "node_pool_name": node_info["node_pool_name"],
                "cluster_name": node_info["cluster_name"],
                "current_image_name": None,
                "current_image_id": None,
                "latest_image_name": None,
                "latest_image_id": None,
                "needs_update": False,
                "status": "unknown",
            }

            try:
                # Get instance details to find current image
                instance = compute_client.get_instance(node_info["node_id"]).data
                image_id = getattr(instance, "image_id", None) or node_info.get("pool_image_id")

                if not image_id:
                    node_result["status"] = "no_image_id"
                    nodes_unknown += 1
                    results.append(node_result)
                    continue

                node_result["current_image_id"] = image_id

                # Get current image details
                try:
                    current_image = compute_client.get_image(image_id).data
                    node_result["current_image_name"] = getattr(
                        current_image, "display_name", image_id
                    )

                    # Try to find LATEST image of same type
                    image_compartment_id = getattr(current_image, "compartment_id", None)
                    defined_tags = getattr(current_image, "defined_tags", {}) or {}

                    # Check for image type in defined tags
                    image_type = None
                    for namespace in ["ics_images", "icm_images"]:
                        ns_tags = defined_tags.get(namespace, {})
                        if isinstance(ns_tags, dict) and "type" in ns_tags:
                            image_type = ns_tags["type"]
                            break

                    if not image_type or not image_compartment_id:
                        node_result["status"] = "no_image_type_tag"
                        nodes_unknown += 1
                        results.append(node_result)
                        continue

                    # Search for LATEST image with same type
                    from oci.pagination import list_call_get_all_results

                    images = list_call_get_all_results(
                        compute_client.list_images,
                        compartment_id=image_compartment_id,
                        sort_by="TIMECREATED",
                        sort_order="DESC",
                    ).data

                    latest_image = None
                    for img in images:
                        img_tags = getattr(img, "defined_tags", {}) or {}
                        img_type = None
                        release = None

                        for namespace in ["ics_images", "icm_images"]:
                            ns_tags = img_tags.get(namespace, {})
                            if isinstance(ns_tags, dict):
                                if "type" in ns_tags:
                                    img_type = ns_tags["type"]
                                if "release" in ns_tags:
                                    release = ns_tags["release"]

                        if img_type == image_type and release and release.upper() == "LATEST":
                            latest_image = img
                            break

                    if latest_image:
                        latest_name = getattr(latest_image, "display_name", None)
                        latest_id = getattr(latest_image, "id", None)
                        node_result["latest_image_name"] = latest_name
                        node_result["latest_image_id"] = latest_id

                        if latest_id != image_id:
                            node_result["needs_update"] = True
                            node_result["status"] = "update_available"
                            nodes_needing_update += 1
                        else:
                            node_result["status"] = "up_to_date"
                            nodes_up_to_date += 1
                    else:
                        node_result["status"] = "no_latest_image_found"
                        nodes_unknown += 1

                except oci_exceptions.ServiceError as e:
                    node_result["status"] = f"image_lookup_error: {e.message}"
                    nodes_unknown += 1

            except oci_exceptions.ServiceError as e:
                node_result["status"] = f"instance_lookup_error: {e.message}"
                nodes_unknown += 1

            results.append(node_result)

        # Build summary
        summary = {
            "project": project,
            "stage": stage,
            "region": region,
            "cluster_id": cluster_id,
            "compartment_id": compartment_id,
            "total_nodes_checked": len(results),
            "nodes_needing_update": nodes_needing_update,
            "nodes_up_to_date": nodes_up_to_date,
            "nodes_unknown": nodes_unknown,
            "nodes_with_updates": [r for r in results if r["needs_update"]],
            "all_nodes": results,
        }

        return [TextContent(type="text", text=json.dumps(summary, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error checking node image updates: {str(e)}")]


# ========== DevOps Tool Handlers ==========


async def _list_devops_projects(arguments: Dict[str, Any]) -> List[TextContent]:
    """List DevOps projects in a compartment."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    compartment_id = _get_compartment_id(project, stage, region, config_file)
    if not compartment_id:
        return [
            TextContent(
                type="text",
                text=f"Error: Could not find compartment ID for {project}/{stage}/{region}",
            )
        ]

    try:
        projects = client.list_devops_projects(compartment_id)
        result = {
            "project": project,
            "stage": stage,
            "region": region,
            "compartment_id": compartment_id,
            "devops_project_count": len(projects),
            "devops_projects": [_serialize_devops_project(p) for p in projects],
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing DevOps projects: {str(e)}")]


async def _list_deployment_pipelines(arguments: Dict[str, Any]) -> List[TextContent]:
    """List deployment pipelines in a DevOps project or compartment."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    devops_project_id = arguments.get("devops_project_id")
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    compartment_id = _get_compartment_id(project, stage, region, config_file)
    if not compartment_id:
        return [
            TextContent(
                type="text",
                text=f"Error: Could not find compartment ID for {project}/{stage}/{region}",
            )
        ]

    try:
        pipelines = client.list_deployment_pipelines(
            compartment_id=compartment_id,
            project_id=devops_project_id,
        )
        result = {
            "project": project,
            "stage": stage,
            "region": region,
            "compartment_id": compartment_id,
            "devops_project_id": devops_project_id,
            "pipeline_count": len(pipelines),
            "pipelines": [_serialize_deployment_pipeline(p) for p in pipelines],
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing deployment pipelines: {str(e)}")]


async def _get_recent_deployment(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get the most recent deployment for a pipeline."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    pipeline_id = arguments["pipeline_id"]
    limit = arguments.get("limit", 1)
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    try:
        deployments = client.get_recent_deployment(pipeline_id, limit=limit)

        if not deployments:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "project": project,
                            "stage": stage,
                            "region": region,
                            "pipeline_id": pipeline_id,
                            "deployment_count": 0,
                            "message": "No deployments found for this pipeline",
                        },
                        indent=2,
                    ),
                )
            ]

        # Build a summary for each deployment
        deployment_summaries = []
        for deployment in deployments:
            status = deployment.lifecycle_state
            is_success = status == "SUCCEEDED"
            is_failed = status == "FAILED"
            is_in_progress = status in ("IN_PROGRESS", "ACCEPTED", "CANCELING")

            # Get failed stages if any
            failed_stages = []
            if deployment.deployment_execution_progress:
                stage_progress = deployment.deployment_execution_progress.get(
                    "deploy_stage_execution_progress", {}
                )
                for stage_id, stage_info in stage_progress.items():
                    if stage_info.get("status") in ("FAILED", "CANCELED", "ROLLBACK_FAILED"):
                        failed_stages.append(
                            {
                                "stage_id": stage_id,
                                "display_name": stage_info.get("deploy_stage_display_name"),
                                "status": stage_info.get("status"),
                            }
                        )

            summary = {
                "deployment_id": deployment.deployment_id,
                "display_name": deployment.display_name,
                "status": status,
                "is_success": is_success,
                "is_failed": is_failed,
                "is_in_progress": is_in_progress,
                "time_started": deployment.time_started,
                "time_finished": deployment.time_finished,
                "lifecycle_details": deployment.lifecycle_details,
                "failed_stages": failed_stages,
                "full_details": _serialize_deployment(deployment),
            }
            deployment_summaries.append(summary)

        result = {
            "project": project,
            "stage": stage,
            "region": region,
            "pipeline_id": pipeline_id,
            "deployment_count": len(deployments),
            "deployments": deployment_summaries,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error getting recent deployment: {str(e)}")]


async def _get_deployment_logs(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get detailed logs for a specific deployment."""
    project = arguments["project"]
    stage = arguments["stage"]
    region = arguments["region"]
    deployment_id = arguments["deployment_id"]
    config_file = arguments.get("config_file", "meta.yaml")

    client, error = _get_client(project, stage, region, config_file)
    if error:
        return [TextContent(type="text", text=f"Error: {error}")]

    try:
        logs = client.get_deployment_logs(deployment_id)

        result = {
            "project": project,
            "stage": stage,
            "region": region,
            **logs,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error getting deployment logs: {str(e)}")]


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

# OKE Operations MCP Server

**Model Context Protocol (MCP) Server for Oracle Kubernetes Engine Operations**

An MCP server that provides AI assistants with tools for performing operational tasks on Oracle Kubernetes Engine (OKE) clusters. This enables Software Engineers to use AI assistants (like Claude) for OKE operational work.

## Key Features

- **Cluster Version Management**: List clusters and check available Kubernetes upgrades
- **Control Plane Upgrades**: Upgrade OKE cluster control planes to latest versions
- **Node Pool Management**: Upgrade node pool configurations and cycle workers
- **Image Updates**: Cycle node pools to apply new node images

## Supported Operations

| Operation | Description |
|-----------|-------------|
| `list_oke_clusters` | List all OKE clusters in a project/stage/region |
| `get_oke_cluster_details` | Get detailed cluster information including node pools |
| `upgrade_oke_cluster` | Upgrade cluster control plane to target version |
| `list_node_pools` | List node pools with current versions |
| `upgrade_node_pool` | Upgrade node pool Kubernetes version configuration |
| `cycle_node_pool` | Replace node boot volumes to apply new images |
| `get_oke_version_report` | Generate version report for all clusters |

## Quick Start

### Prerequisites

- Python 3.10+
- OCI CLI installed and configured
- Access to Oracle Cloud Infrastructure
- Poetry for dependency management

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd oracle-sdk-client

# Install dependencies
make install
```

### Configuration

Create or update `tools/meta.yaml` with your project/stage/region mappings:

```yaml
projects:
  remote-observer:
    dev:
      oc1:
        us-phoenix-1:
          compartment_id: ocid1.compartment.oc1..aaaaaaaah3k3f5rksyb5iv...
    staging:
      oc1:
        us-ashburn-1:
          compartment_id: ocid1.compartment.oc1..aaaaaaaasrzpupgdi2aa7l...
    prod:
      oc17:
        us-dcc-phoenix-1:
          compartment_id: ocid1.compartment.oc17..aaaaaaaasaow4j73qa6mf4...
```

### Authentication Setup

```bash
# Create OCI session token
oci session authenticate --profile-name DEFAULT --region us-phoenix-1
```

### Running the MCP Server

```bash
# Run the MCP server
make mcp-server

# Or run directly with Python
cd tools && poetry run python src/mcp_server.py
```

### Using with Claude Desktop

Add to your Claude Desktop configuration (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "oke-operations": {
      "command": "poetry",
      "args": ["run", "python", "src/mcp_server.py"],
      "cwd": "/path/to/oracle-sdk-client/tools"
    }
  }
}
```

## Usage Examples

### 1. Upgrade OKE Cluster Version to Latest

Ask your AI assistant:
> "Upgrade the OKE cluster in remote-observer dev us-phoenix-1 to the latest version"

The assistant will:
1. List clusters to find the target cluster
2. Check available upgrades
3. Initiate the control plane upgrade
4. Report the work request ID for tracking

### 2. Upgrade Node Pool Images

Ask your AI assistant:
> "Upgrade the node pools in cluster X to the latest Kubernetes version and cycle the nodes"

The assistant will:
1. Get cluster details and node pools
2. Upgrade node pool configurations
3. Cycle node pools to replace boot volumes

### 3. Restart/Upgrade OKE Cluster Nodes

Ask your AI assistant:
> "Cycle all node pools in the production cluster to apply the new node images"

The assistant will:
1. List node pools in the cluster
2. Initiate boot volume replacement for each pool
3. Report progress and work request IDs

## MCP Tools Reference

### list_oke_clusters

List all OKE clusters for a project/stage/region.

**Parameters:**
- `project` (required): Project name (e.g., 'remote-observer')
- `stage` (required): Stage name (e.g., 'dev', 'staging', 'prod')
- `region` (required): OCI region (e.g., 'us-phoenix-1')

### get_oke_cluster_details

Get detailed information about a specific OKE cluster.

**Parameters:**
- `project`, `stage`, `region` (required)
- `cluster_id` (required): OKE cluster OCID

### upgrade_oke_cluster

Upgrade OKE cluster control plane to a target version.

**Parameters:**
- `project`, `stage`, `region`, `cluster_id` (required)
- `target_version` (optional): Target K8s version (defaults to latest)
- `dry_run` (optional): Preview without making changes

### list_node_pools

List all node pools for an OKE cluster.

**Parameters:**
- `project`, `stage`, `region`, `cluster_id` (required)

### upgrade_node_pool

Upgrade node pool Kubernetes version configuration.

**Parameters:**
- `project`, `stage`, `region`, `node_pool_id`, `target_version` (required)
- `dry_run` (optional): Preview without making changes

### cycle_node_pool

Cycle node pool workers by replacing boot volumes.

**Parameters:**
- `project`, `stage`, `region`, `node_pool_id` (required)
- `maximum_unavailable` (optional): Max unavailable nodes (default: 1)
- `maximum_surge` (optional): Max additional nodes during cycling
- `dry_run` (optional): Preview without making changes

### get_oke_version_report

Generate a version report for all OKE clusters.

**Parameters:**
- `project`, `stage` (required)

## CLI Tools

In addition to the MCP server, traditional CLI tools are available:

```bash
# Generate OKE version report
make oke-version-report PROJECT=remote-observer STAGE=dev

# Upgrade OKE cluster control plane
make oke-upgrade REPORT=reports/oke_versions_remote-observer_dev.html

# Upgrade node pools
make oke-upgrade-node-pools REPORT=reports/oke_versions_remote-observer_dev.html

# Cycle node pools
make oke-node-cycle REPORT=reports/oke_versions_remote-observer_dev.html

# Bump node pool images from CSV
make oke-node-pool-bump CSV=oci_image_updates_report.csv
```

## Project Structure

```
oracle-sdk-client/
├── tools/
│   ├── src/
│   │   ├── mcp_server.py          # MCP server implementation
│   │   ├── oci_client/            # OCI client library
│   │   │   ├── client.py          # Main OCI client
│   │   │   ├── models.py          # Data models
│   │   │   ├── auth.py            # Authentication
│   │   │   └── utils/             # Utility modules
│   │   ├── oke_upgrade.py         # Cluster upgrade CLI
│   │   ├── oke_node_pool_upgrade.py  # Node pool upgrade CLI
│   │   ├── oke_node_cycle.py      # Node cycling CLI
│   │   └── oke_version_report.py  # Version report generator
│   ├── tests/                     # Unit tests
│   ├── meta.yaml                  # Configuration (gitignored)
│   └── pyproject.toml             # Dependencies
├── README.md                      # This file
└── Makefile                       # Automation commands
```

## Development

### Setup Development Environment

```bash
make dev-setup
```

### Run Tests

```bash
make test
```

### Code Quality

```bash
make format    # Format code
make lint      # Run linting
make type-check # Run type checking
make check     # Run all checks
```

## Security

- Session tokens automatically managed (1-hour expiry)
- No credentials stored in code or configuration
- Bastion-based access for private instances
- Uses OCI SDK security best practices

## Troubleshooting

### Authentication Issues

```bash
# Refresh session token
oci session authenticate --profile-name DEFAULT --region us-phoenix-1
```

### No Clusters Found

- Verify compartment IDs in `meta.yaml`
- Check OCI permissions for the authenticated user
- Ensure clusters exist in the specified regions

### Upgrade Failures

- Check cluster lifecycle state is ACTIVE
- Verify target version is in available_upgrades
- Review OCI work request for detailed errors

## Support

For issues and questions:
1. Check troubleshooting section above
2. Review OCI documentation
3. Verify OCI CLI configuration and permissions

---

**OKE Operations MCP Server** - Enabling AI-assisted Oracle Kubernetes Engine operations

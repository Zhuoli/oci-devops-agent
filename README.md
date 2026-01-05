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

### Using with OpenCode

[OpenCode](https://opencode.ai) provides an enhanced AI coding experience with Skills support. This repository includes pre-built Skills that guide the AI through complex OKE operational workflows.

#### OpenCode Configuration

Add the MCP server to your OpenCode configuration (`~/.config/opencode/config.json` or `opencode.json` in your project):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcpServers": {
    "oke-operations": {
      "command": "poetry",
      "args": ["run", "python", "src/mcp_server.py"],
      "cwd": "/path/to/oracle-sdk-client/tools"
    }
  }
}
```

#### Available Skills

This repository includes two OpenCode Skills in `.opencode/skills/`:

| Skill | Description | Use Case |
|-------|-------------|----------|
| `oke-cluster-upgrade` | Full Kubernetes version upgrade workflow | Upgrade control-plane, node pool configs, and roll out to workers |
| `oke-node-upgrade` | Node image update workflow | Apply security patches, OS updates via node cycling |

Skills are automatically discovered when you open this repository in OpenCode.

#### How Skills + MCP Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                         OpenCode                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │     Skills      │    │           MCP Server                │ │
│  │  (Procedures)   │    │           (Tools)                   │ │
│  ├─────────────────┤    ├─────────────────────────────────────┤ │
│  │ oke-cluster-    │───▶│ list_oke_clusters                   │ │
│  │ upgrade         │    │ get_oke_cluster_details             │ │
│  │                 │    │ upgrade_oke_cluster                 │ │
│  │ Guides AI       │    │ upgrade_node_pool                   │ │
│  │ through the     │    │ cycle_node_pool                     │ │
│  │ correct order   │    │                                     │ │
│  │ of operations   │    │ Executes actual OCI API calls       │ │
│  ├─────────────────┤    ├─────────────────────────────────────┤ │
│  │ oke-node-       │───▶│ list_oke_clusters                   │ │
│  │ upgrade         │    │ list_node_pools                     │ │
│  │                 │    │ cycle_node_pool                     │ │
│  │ Guides AI       │    │ get_oke_version_report              │ │
│  │ through node    │    │                                     │ │
│  │ image updates   │    │ Executes actual OCI API calls       │ │
│  └─────────────────┘    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Skills** define the procedural workflow (what to do, in what order, with what checks).
**MCP Tools** provide the actual capabilities (API calls to OCI).

#### Example: Using Skills in OpenCode

1. **Open this repository** in OpenCode
2. **Invoke a skill** by asking the AI:

   For cluster Kubernetes version upgrade:
   > "Use the oke-cluster-upgrade skill to upgrade the OKE cluster in remote-observer dev us-phoenix-1"

   For node image updates:
   > "Use the oke-node-upgrade skill to cycle all node pools in the staging cluster"

3. **The AI will**:
   - Load the skill's procedural instructions
   - Execute MCP tools in the correct order
   - Handle decision points (dry-run first, confirm before execution)
   - Provide status updates and summary reports

#### Skill Workflow: OKE Cluster Upgrade

The `oke-cluster-upgrade` skill guides through a 4-phase process:

```
Phase 1: Discovery          Phase 2: Control Plane
┌─────────────────────┐    ┌─────────────────────┐
│ list_oke_clusters   │───▶│ upgrade_oke_cluster │
│ get_cluster_details │    │ (dry_run=true)      │
│ Select version      │    │ upgrade_oke_cluster │
└─────────────────────┘    │ (dry_run=false)     │
                           └──────────┬──────────┘
                                      │
                                      ▼
Phase 4: Node Rollout       Phase 3: Data Plane
┌─────────────────────┐    ┌─────────────────────┐
│ cycle_node_pool     │◀───│ list_node_pools     │
│ (for each pool)     │    │ upgrade_node_pool   │
│ Verify completion   │    │ (for each pool)     │
└─────────────────────┘    └─────────────────────┘
```

#### Skill Workflow: OKE Node Upgrade

The `oke-node-upgrade` skill handles node image updates:

```
Phase 1: Discovery          Phase 2: Planning
┌─────────────────────┐    ┌─────────────────────┐
│ list_oke_clusters   │───▶│ Select scope        │
│ get_cluster_details │    │ (all/specific pools)│
│ list_node_pools     │    │ Set cycling params  │
└─────────────────────┘    └──────────┬──────────┘
                                      │
                                      ▼
Phase 4: Verification       Phase 3: Execution
┌─────────────────────┐    ┌─────────────────────┐
│ get_cluster_details │◀───│ cycle_node_pool     │
│ Confirm all ACTIVE  │    │ (dry_run=true)      │
│ Report summary      │    │ cycle_node_pool     │
└─────────────────────┘    │ (dry_run=false)     │
                           └─────────────────────┘
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
├── .opencode/
│   └── skills/                    # OpenCode Skills for guided workflows
│       ├── oke-cluster-upgrade/
│       │   └── SKILL.md           # K8s version upgrade procedure
│       └── oke-node-upgrade/
│           └── SKILL.md           # Node image update procedure
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

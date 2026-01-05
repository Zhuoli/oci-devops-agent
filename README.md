# OCI DevOps Plugin for OpenCode

**An OpenCode CLI plugin enabling AI-assisted Oracle Cloud Infrastructure operations**

This plugin extends [OpenCode CLI](https://opencode.ai) with specialized tools, skills, and agent instructions for performing DevOps tasks on Oracle Cloud Infrastructure (OCI), with a focus on Oracle Kubernetes Engine (OKE) operations.

## What This Plugin Provides

| Component | Description |
|-----------|-------------|
| **MCP Server** | Model Context Protocol server providing OCI/OKE operational tools |
| **Skills** | Guided workflows for complex multi-step OKE operations |
| **AGENTS.md** | Repository-specific instructions and safety guidelines |

## Key Features

- **Cluster Version Management**: List clusters and check available Kubernetes upgrades
- **Control Plane Upgrades**: Upgrade OKE cluster control planes to latest versions
- **Node Pool Management**: Upgrade node pool configurations and cycle workers
- **Image Updates**: Cycle node pools to apply new node images
- **Safety Controls**: Built-in dry-run support and approval checkpoints for mutating operations

---

## Installation Guide

### Step 1: Install OpenCode CLI

Choose one of the following installation methods:

#### Quick Install (Recommended)
```bash
curl -fsSL https://opencode.ai/install | bash
```

#### Package Managers

| Platform | Command |
|----------|---------|
| **npm** | `npm i -g opencode-ai@latest` |
| **Homebrew** | `brew install opencode` |
| **Go** | `go install github.com/opencode-ai/opencode@latest` |
| **Arch Linux** | `paru -S opencode-bin` |
| **Windows (Scoop)** | `scoop bucket add extras && scoop install extras/opencode` |
| **Windows (Chocolatey)** | `choco install opencode` |
| **Nix** | `nix run nixpkgs#opencode` |

### Step 2: Configure an AI Provider

OpenCode requires an AI provider. Set one of the following environment variables:

```bash
# Claude (Anthropic) - Recommended
export ANTHROPIC_API_KEY="your-key"

# Or use OpenCode Zen (run /connect in OpenCode TUI)
# Or OpenAI
export OPENAI_API_KEY="your-key"

# Or Google Gemini
export GEMINI_API_KEY="your-key"
```

### Step 3: Clone This Repository

```bash
git clone https://github.com/Zhuoli/oci-devops-agent.git
cd oci-devops-agent
```

### Step 4: Install Python Dependencies

```bash
# Requires Python 3.10+ and Poetry
make install
```

### Step 5: Configure OCI Authentication

```bash
# Create OCI session token
oci session authenticate --profile-name DEFAULT --region us-phoenix-1
```

### Step 6: Configure Project Mappings

Create or update `tools/meta.yaml` with your OCI project/stage/region mappings:

```yaml
projects:
  my-project:
    dev:
      oc1:
        us-phoenix-1:
          compartment_id: ocid1.compartment.oc1..aaaaaaaah3k3f5rk...
    staging:
      oc1:
        us-ashburn-1:
          compartment_id: ocid1.compartment.oc1..aaaaaaaasrzpupgd...
    prod:
      oc17:
        us-dcc-phoenix-1:
          compartment_id: ocid1.compartment.oc17..aaaaaaaasaow4j73...
```

### Step 7: Add MCP Server to OpenCode

Add the MCP server configuration to your OpenCode config file.

**Location**: `~/.config/opencode/opencode.json` (global) or `opencode.json` (project-local)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcpServers": {
    "oci-devops": {
      "type": "stdio",
      "command": "poetry",
      "args": ["run", "python", "src/mcp_server.py"],
      "cwd": "/path/to/oci-devops-agent/tools"
    }
  }
}
```

### Step 8: Install Skills

OpenCode skills provide guided workflows for complex operations. This repository includes two skills in `.opencode/skills/`.

#### Option A: Use This Repository Directly

When you run OpenCode from within this repository, skills are automatically discovered from `.opencode/skills/`.

```bash
cd oci-devops-agent
opencode
```

#### Option B: Copy Skills to Global Location

Copy skills to your global OpenCode config for use in any project:

```bash
# Create global skills directory
mkdir -p ~/.config/opencode/skill

# Copy skills
cp -r .opencode/skills/oke-cluster-upgrade ~/.config/opencode/skill/
cp -r .opencode/skills/oke-node-upgrade ~/.config/opencode/skill/
```

### Step 9: Add AGENTS.md Instructions

The `AGENTS.md` file provides repository guidelines and safety instructions to the AI agent.

#### Option A: Use This Repository Directly

The `AGENTS.md` at the root of this repository is automatically loaded when running OpenCode here.

#### Option B: Copy to Your Project

Copy `AGENTS.md` to your project root or merge its contents with your existing `AGENTS.md`:

```bash
cp AGENTS.md /path/to/your-project/
```

#### Option C: Add to Global Config

For global instructions across all projects:

```bash
cp AGENTS.md ~/.config/opencode/AGENTS.md
```

---

## Available Skills

| Skill | Description | Invoke With |
|-------|-------------|-------------|
| `oke-cluster-upgrade` | Full Kubernetes version upgrade: control-plane, node pool configs, and worker rollout | "Use the oke-cluster-upgrade skill to upgrade..." |
| `oke-node-upgrade` | Node image update workflow: apply security patches, OS updates via node cycling | "Use the oke-node-upgrade skill to cycle..." |

### How Skills + MCP Work Together

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

---

## MCP Tools Reference

### Read-Only Operations

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_oke_clusters` | List all OKE clusters | `project`, `stage`, `region` |
| `get_oke_cluster_details` | Get detailed cluster info | `project`, `stage`, `region`, `cluster_id` |
| `list_node_pools` | List node pools for a cluster | `project`, `stage`, `region`, `cluster_id` |
| `get_oke_version_report` | Generate version report | `project`, `stage` |

### Mutating Operations (Require User Approval)

| Tool | Description | Parameters |
|------|-------------|------------|
| `upgrade_oke_cluster` | Upgrade control plane | `project`, `stage`, `region`, `cluster_id`, `target_version`, `dry_run` |
| `upgrade_node_pool` | Upgrade node pool config | `project`, `stage`, `region`, `node_pool_id`, `target_version`, `dry_run` |
| `cycle_node_pool` | Replace worker nodes | `project`, `stage`, `region`, `node_pool_id`, `maximum_unavailable`, `dry_run` |

---

## Usage Examples

### Using Skills (Recommended)

Skills provide guided, step-by-step workflows with safety checkpoints.

**Upgrade Kubernetes version:**
```
Use the oke-cluster-upgrade skill to upgrade the OKE cluster in my-project dev us-phoenix-1
```

**Apply node image updates:**
```
Use the oke-node-upgrade skill to cycle all node pools in the staging cluster
```

### Direct Tool Usage

For simple operations, you can use MCP tools directly.

**List clusters:**
```
List all OKE clusters in my-project dev us-phoenix-1
```

**Check upgrade availability:**
```
Get details for cluster X and show me available upgrades
```

---

## Safety Features

### User Approval Requirements

**CRITICAL: Mutating operations require explicit user approval.**

| Operation Type | Tools | Approval Required |
|---------------|-------|-------------------|
| Read-only | `list_oke_clusters`, `get_oke_cluster_details`, `list_node_pools`, `get_oke_version_report` | No |
| **Mutating** | `upgrade_oke_cluster`, `upgrade_node_pool`, `cycle_node_pool` | **YES** |

### Approval Workflow

1. **Dry-run first**: Use `dry_run=true` to preview changes
2. **Review the plan**: AI presents what will be modified
3. **Explicit approval**: AI waits for your "yes" before proceeding
4. **Per-operation approval**: Each mutating operation requires separate confirmation

---

## Project Structure

```
oci-devops-agent/
├── .opencode/
│   └── skills/                    # OpenCode Skills
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
├── AGENTS.md                      # Repository guidelines for AI
├── README.md                      # This file
└── Makefile                       # Automation commands
```

---

## CLI Tools (Alternative Usage)

In addition to the AI-assisted workflow, traditional CLI tools are available:

```bash
# Generate OKE version report
make oke-version-report PROJECT=my-project STAGE=dev

# Upgrade OKE cluster control plane
make oke-upgrade REPORT=reports/oke_versions_my-project_dev.html

# Upgrade node pools
make oke-upgrade-node-pools REPORT=reports/oke_versions_my-project_dev.html

# Cycle node pools
make oke-node-cycle REPORT=reports/oke_versions_my-project_dev.html
```

---

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

### Run MCP Server Locally

```bash
make mcp-server
# Or directly:
cd tools && poetry run python src/mcp_server.py
```

---

## Troubleshooting

### OpenCode Not Finding Skills

- Ensure you're running OpenCode from within the repository, OR
- Copy skills to `~/.config/opencode/skill/`
- Check skill folder structure: `skill-name/SKILL.md`

### MCP Server Not Connecting

- Verify the `cwd` path in your OpenCode config is absolute
- Ensure Poetry is installed and dependencies are available
- Test manually: `cd tools && poetry run python src/mcp_server.py`

### Authentication Issues

```bash
# Refresh OCI session token
oci session authenticate --profile-name DEFAULT --region us-phoenix-1
```

### No Clusters Found

- Verify compartment IDs in `meta.yaml`
- Check OCI permissions for the authenticated user
- Ensure clusters exist in the specified regions

---

## Resources

- [OpenCode Documentation](https://opencode.ai/docs/)
- [OpenCode CLI Reference](https://opencode.ai/docs/cli/)
- [OpenCode Skills Guide](https://opencode.ai/docs/skills/)
- [OpenCode Configuration](https://opencode.ai/docs/config/)
- [AGENTS.md Specification](https://agents.md/)
- [OCI Documentation](https://docs.oracle.com/en-us/iaas/Content/ContEng/home.htm)

---

**OCI DevOps Plugin for OpenCode** - Enabling AI-assisted Oracle Cloud Infrastructure operations

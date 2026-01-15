# OCI DevOps Tools

**CLI tools and Skills for AI-assisted Oracle Cloud Infrastructure operations**

This project provides Skills and CLI tools for performing DevOps tasks on Oracle Cloud Infrastructure (OCI), with a focus on Oracle Kubernetes Engine (OKE) operations. Skills describe how to invoke CLI tools with proper parameters and interpret their outputs.

## What This Project Provides

| Component | Description |
|-----------|-------------|
| **Skills** | Guided workflows that invoke CLI tools for OCI operations |
| **CLI Tools** | Makefile targets for OKE and infrastructure management |
| **AGENTS.md** | Repository-specific instructions and safety guidelines |

## Key Features

- **Cluster Version Management**: Generate reports of all clusters and available Kubernetes upgrades
- **Control Plane Upgrades**: Upgrade OKE cluster control planes to latest versions
- **Node Pool Management**: Upgrade node pool configurations and cycle workers
- **Image Updates**: Check for and apply new node images via node pool cycling
- **SSH Configuration**: Generate SSH configs for OCI instances with bastion access
- **Resource Management**: Delete buckets and clusters when needed
- **Safety Controls**: Built-in dry-run support and approval checkpoints for mutating operations

---

## Installation Guide

### Step 1: Install OpenCode CLI (Optional)

If using with OpenCode CLI for AI-assisted workflows:

```bash
curl -fsSL https://opencode.ai/install | bash
```

### Step 2: Configure an AI Provider (Optional)

For AI-assisted usage:

```bash
# Claude (Anthropic) - Recommended
export ANTHROPIC_API_KEY="your-key"
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

Create or update `tools/meta.yaml` with your OCI project/stage/realm/tenancy/region mappings:

```yaml
projects:
  my-project:
    dev:
      oc1:
        tenancy-ocid: ocid1.tenancy.oc1..aaaaaaaah3k3f5rk...
        tenancy-name: "my-dev-tenancy"
        us-phoenix-1:
          compartment_id: ocid1.compartment.oc1..aaaaaaaah3k3f5rk...
    staging:
      oc1:
        tenancy-ocid: ocid1.tenancy.oc1..aaaaaaaasrzpupgd...
        tenancy-name: "my-staging-tenancy"
        us-ashburn-1:
          compartment_id: ocid1.compartment.oc1..aaaaaaaasrzpupgd...
```

### Step 7: Install Skills (For AI-Assisted Usage)

Skills are automatically discovered from `.opencode/skills/` when running OpenCode from this repository.

```bash
cd oci-devops-agent
opencode
```

Or copy skills to global location:

```bash
mkdir -p ~/.config/opencode/skill
cp -r .opencode/skills/* ~/.config/opencode/skill/
```

---

## Available Skills

### OKE Operations

| Skill | Description | Invoke With |
|-------|-------------|-------------|
| `oke-version-report` | Generate HTML report of cluster versions | "Generate a version report for my-project dev" |
| `oke-upgrade` | Upgrade cluster control planes | "Upgrade the OKE clusters" |
| `oke-upgrade-node-pools` | Upgrade node pool configurations | "Upgrade the node pools" |
| `oke-node-cycle` | Cycle workers to apply new images | "Cycle the node pools" |
| `oke-node-pool-bump` | Update node images from CSV report | "Apply image updates from CSV" |
| `oke-cluster-upgrade` | Full K8s version upgrade workflow | "Use the oke-cluster-upgrade skill" |
| `oke-node-upgrade` | Node image update workflow | "Use the oke-node-upgrade skill" |

### SSH & Infrastructure

| Skill | Description | Invoke With |
|-------|-------------|-------------|
| `ssh-sync` | Generate SSH config for instances | "Generate SSH config for dev" |
| `ssh-help` | Show SSH configuration help | "Show SSH help" |
| `image-updates` | Check for available image updates | "Check for image updates" |

### Resource Management

| Skill | Description | Invoke With |
|-------|-------------|-------------|
| `delete-bucket` | Delete an OCI bucket | "Delete the bucket" |
| `delete-oke-cluster` | Delete an OKE cluster | "Delete the cluster" |

---

## How Skills + CLI Tools Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                         OpenCode                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │     Skills      │    │          CLI Tools (Makefile)       │ │
│  │  (Procedures)   │    │                                     │ │
│  ├─────────────────┤    ├─────────────────────────────────────┤ │
│  │ oke-version-    │───▶│ make oke-version-report             │ │
│  │ report          │    │                                     │ │
│  ├─────────────────┤    ├─────────────────────────────────────┤ │
│  │ oke-upgrade     │───▶│ make oke-upgrade                    │ │
│  ├─────────────────┤    ├─────────────────────────────────────┤ │
│  │ oke-node-cycle  │───▶│ make oke-node-cycle                 │ │
│  ├─────────────────┤    ├─────────────────────────────────────┤ │
│  │ image-updates   │───▶│ make image-updates                  │ │
│  └─────────────────┘    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Skills** define the procedural workflow (what to do, in what order, with what checks).
**CLI Tools** provide the actual capabilities (run commands, produce output files).

---

## CLI Tools Reference

### OKE Operations

| Command | Description | Output |
|---------|-------------|--------|
| `make oke-version-report PROJECT=x STAGE=y` | Generate cluster version report | HTML file |
| `make oke-upgrade REPORT=path [DRY_RUN=true]` | Upgrade cluster control planes | Console |
| `make oke-upgrade-node-pools REPORT=path` | Upgrade node pool configs | Console |
| `make oke-node-cycle REPORT=path` | Cycle node pools | Console |
| `make oke-node-pool-bump CSV=path` | Bump images from CSV | Console |

### SSH & Infrastructure

| Command | Description | Output |
|---------|-------------|--------|
| `make ssh-sync PROJECT=x STAGE=y` | Generate SSH config | SSH config file |
| `make ssh-help` | Show SSH configuration help | Console |
| `make image-updates PROJECT=x STAGE=y` | Check for image updates | CSV + Console |

### Resource Management

| Command | Description | Output |
|---------|-------------|--------|
| `make delete-bucket PROJECT=x STAGE=y REGION=r BUCKET=b` | Delete bucket | Console |
| `make delete-oke-cluster PROJECT=x STAGE=y REGION=r CLUSTER_ID=id` | Delete cluster | Console |

---

## Usage Examples

### Using Skills (AI-Assisted)

Skills provide guided, step-by-step workflows with safety checkpoints.

**Upgrade Kubernetes version:**
```
Use the oke-cluster-upgrade skill to upgrade the OKE cluster in my-project dev
```

**Apply node image updates:**
```
Use the oke-node-upgrade skill to cycle all node pools in the staging cluster
```

**Check cluster versions:**
```
Use the oke-version-report skill to check what clusters we have in my-project dev
```

### Direct CLI Usage

For direct command-line usage without AI assistance:

```bash
# Generate version report
make oke-version-report PROJECT=my-project STAGE=dev

# Preview upgrade (dry-run)
make oke-upgrade REPORT=reports/oke_versions_my-project_dev.html DRY_RUN=true

# Execute upgrade
make oke-upgrade REPORT=reports/oke_versions_my-project_dev.html

# Check for image updates
make image-updates PROJECT=my-project STAGE=dev

# Generate SSH config
make ssh-sync PROJECT=my-project STAGE=dev
```

---

## Safety Features

### User Approval Requirements

**CRITICAL: Mutating operations require explicit user approval.**

| Operation Type | CLI Commands | Approval Required |
|---------------|--------------|-------------------|
| Read-only | `oke-version-report`, `image-updates`, `ssh-sync` | No |
| **Mutating** | `oke-upgrade`, `oke-upgrade-node-pools`, `oke-node-cycle`, `oke-node-pool-bump` | **YES** |
| **Destructive** | `delete-bucket`, `delete-oke-cluster` | **YES - Extra confirmation** |

### Approval Workflow

1. **Dry-run first**: Use `DRY_RUN=true` to preview changes
2. **Review the plan**: AI presents what will be modified
3. **Explicit approval**: AI waits for your "yes" before proceeding
4. **Per-operation approval**: Each mutating operation requires separate confirmation

---

## Project Structure

```
oci-devops-agent/
├── .opencode/
│   └── skills/                    # OpenCode Skills
│       ├── oke-version-report/
│       ├── oke-upgrade/
│       ├── oke-upgrade-node-pools/
│       ├── oke-node-cycle/
│       ├── oke-node-pool-bump/
│       ├── oke-cluster-upgrade/   # Composite workflow
│       ├── oke-node-upgrade/      # Composite workflow
│       ├── ssh-sync/
│       ├── ssh-help/
│       ├── image-updates/
│       ├── delete-bucket/
│       └── delete-oke-cluster/
├── tools/
│   ├── src/
│   │   ├── oci_client/            # OCI client library
│   │   │   ├── client.py          # Main OCI client
│   │   │   ├── models.py          # Data models
│   │   │   ├── auth.py            # Authentication
│   │   │   └── utils/             # Utility modules
│   │   ├── oke_upgrade.py         # Cluster upgrade CLI
│   │   ├── oke_node_pool_upgrade.py  # Node pool upgrade CLI
│   │   ├── oke_node_cycle.py      # Node cycling CLI
│   │   ├── oke_version_report.py  # Version report generator
│   │   ├── check_image_updates.py # Image update checker
│   │   ├── ssh_sync.py            # SSH config generator
│   │   ├── node_cycle_pools.py    # CSV-driven node cycling
│   │   └── delete_resources.py    # Resource deletion
│   ├── tests/                     # Unit tests
│   ├── meta.yaml                  # Configuration (gitignored)
│   └── pyproject.toml             # Dependencies
├── AGENTS.md                      # Repository guidelines for AI
├── README.md                      # This file
└── Makefile                       # CLI commands
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

---

## Troubleshooting

### OpenCode Not Finding Skills

- Ensure you're running OpenCode from within the repository, OR
- Copy skills to `~/.config/opencode/skill/`
- Check skill folder structure: `skill-name/SKILL.md`

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
- [OpenCode Skills Guide](https://opencode.ai/docs/skills/)
- [AGENTS.md Specification](https://agents.md/)
- [OCI Documentation](https://docs.oracle.com/en-us/iaas/Content/ContEng/home.htm)

---

**OCI DevOps Tools** - Enabling AI-assisted Oracle Cloud Infrastructure operations

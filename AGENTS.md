# OCI DevOps Agent

**AI agents MUST use CLI tools via Makefile targets to interact with Oracle Cloud Infrastructure (OCI) resources.** Use the skills in `.opencode/skills/` which describe how to invoke these tools with proper parameters and interpret their outputs.

## Skills

Refer to `.opencode/skills/` for guided workflows on:

- **OKE Operations**: `oke-version-report`, `oke-upgrade`, `oke-upgrade-node-pools`, `oke-node-cycle`, `oke-node-pool-bump`
- **Composite Workflows**: `oke-cluster-upgrade`, `oke-node-upgrade`
- **SSH Configuration**: `ssh-sync`, `ssh-help`
- **Image Management**: `image-updates`
- **Resource Deletion**: `delete-bucket`, `delete-oke-cluster`

## Usage Examples

```
User: What OKE clusters do we have in my-project dev?
Agent: Use the oke-version-report skill to generate a report.
       Run: make oke-version-report PROJECT=my-project STAGE=dev

User: Upgrade the OKE cluster to the latest version
Agent: Use the oke-upgrade skill. First dry-run, then get approval.
       Run: make oke-upgrade REPORT=<path> DRY_RUN=true

User: Are there node image updates available?
Agent: Use the image-updates skill.
       Run: make image-updates PROJECT=my-project STAGE=dev

User: Cycle the node pools to apply new images
Agent: Use the oke-node-cycle skill. Get user approval first.
       Run: make oke-node-cycle REPORT=<path> DRY_RUN=true

User: Generate SSH config for dev instances
Agent: Use the ssh-sync skill.
       Run: make ssh-sync PROJECT=my-project STAGE=dev
```

## CLI Commands Quick Reference

| Command | Purpose |
|---------|---------|
| `make oke-version-report PROJECT=x STAGE=y` | Generate cluster version HTML report |
| `make oke-upgrade REPORT=path DRY_RUN=true` | Preview cluster control plane upgrade |
| `make oke-upgrade REPORT=path` | Execute cluster upgrade |
| `make oke-upgrade-node-pools REPORT=path` | Upgrade node pool configurations |
| `make oke-node-cycle REPORT=path` | Cycle nodes to apply new images |
| `make image-updates PROJECT=x STAGE=y` | Check for image updates (outputs CSV) |
| `make oke-node-pool-bump CSV=path` | Apply image updates from CSV |
| `make ssh-sync PROJECT=x STAGE=y` | Generate SSH config |
| `make delete-bucket PROJECT=x STAGE=y REGION=r BUCKET=b` | Delete bucket |
| `make delete-oke-cluster PROJECT=x STAGE=y REGION=r CLUSTER_ID=id` | Delete cluster |

## Safety Requirements

- **Mutating operations** (upgrades, node cycling, deletions) require explicit user approval
- **Always dry-run first** with `DRY_RUN=true` before any mutating operation
- **Get confirmation** before making changes - wait for user to respond "yes"
- **Destructive operations** (delete-bucket, delete-oke-cluster) require extra confirmation
- Present the impact and ask for explicit approval before executing

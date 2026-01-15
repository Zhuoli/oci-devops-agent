---
name: oke-upgrade-node-pools
description: Cascade node pool Kubernetes version upgrades after the control plane has been upgraded. Updates node pool configurations to match the cluster version.
metadata:
  version: "1.0"
  category: "devops"
---

# OKE Node Pool Upgrade

Upgrade OKE node pool configurations to match the cluster Kubernetes version. This should be run after the control plane upgrade completes.

## User Approval Requirements

**CRITICAL: This skill performs mutating operations that require explicit user approval.**

| Operation | Approval Required |
|-----------|-------------------|
| Dry-run (preview) | No |
| **Actual upgrade** | **YES - MUST WAIT FOR USER CONFIRMATION** |

## When to Use This Skill

- "Upgrade the node pools"
- "Cascade the upgrade to node pools"
- "Update node pool versions to match the cluster"
- After cluster control plane upgrade completes

## Prerequisites

- **REPORT**: Path to HTML report (regenerate after control plane upgrade to get current state)

Optional filters:
- **TARGET_VERSION**: Specific version (defaults to cluster control plane version)
- **PROJECT**, **STAGE**, **REGION_FILTER**, **CLUSTER**: Filter options
- **NODE_POOL**: Filter by specific node pool name or OCID

## CLI Tool Reference

### Command
```bash
# Dry-run first (always do this)
make oke-upgrade-node-pools REPORT=<path> DRY_RUN=true

# Actual upgrade (only after user approval)
make oke-upgrade-node-pools REPORT=<path> [TARGET_VERSION=<version>] [NODE_POOL=<name_or_id>]
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| REPORT | Yes | Path to HTML report file | reports/oke_versions_my-project_dev.html |
| TARGET_VERSION | No | Target K8s version | 1.34.1 |
| PROJECT | No | Filter by project | my-project |
| STAGE | No | Filter by stage | dev |
| REGION_FILTER | No | Filter by region | us-phoenix-1 |
| CLUSTER | No | Filter by cluster | my-cluster |
| NODE_POOL | No | Filter by node pool (can repeat) | pool1 |
| DRY_RUN | No | Preview only | true |
| VERBOSE | No | Detailed output | true |

### Output Format

**Console output** showing:
- Node pools to be upgraded
- Current version -> Target version
- Work request IDs for each upgrade

### Output Interpretation

- **Configuration update only**: This updates node pool CONFIG, not running nodes
- **Nodes need cycling**: After this completes, run oke-node-cycle skill to apply changes to worker nodes

## Procedure

1. **Verify control plane upgrade completed first**
   - Regenerate the version report if needed:
     ```bash
     make oke-version-report PROJECT=<project> STAGE=<stage>
     ```
   - Confirm cluster shows no available upgrades

2. **Always dry-run first**:
   ```bash
   make oke-upgrade-node-pools REPORT=<path> DRY_RUN=true
   ```

3. **Review dry-run output** and present to user:
   ```
   The following node pools will be upgraded:
   - Cluster: <cluster_name>
     - Node Pool: <pool_name> - v1.33.0 -> v1.34.1
   ```

4. **APPROVAL CHECKPOINT**:
   ```
   Ready to upgrade node pool configurations:
   - Node Pool: <name> - v1.33.0 -> v1.34.1

   Note: This updates configuration only. Existing worker nodes will continue
   running the old version until you cycle them with the oke-node-cycle skill.

   Do you approve? (yes/no)
   ```

   **DO NOT PROCEED until user explicitly responds "yes"**

5. **Execute** (only after approval):
   ```bash
   make oke-upgrade-node-pools REPORT=<path>
   ```

6. **Report results** and remind user about next step

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Control plane not ready | Upgrade still in progress | Wait for control plane upgrade to complete |
| Node pool already at version | Already upgraded | Skip - no action needed |
| Version mismatch | Target > control plane | Use cluster version or lower |

## Summary Report

After execution, report:
- Number of node pools upgraded
- Work request IDs for tracking
- **Important reminder**: "Run the oke-node-cycle skill to apply changes to running worker nodes"

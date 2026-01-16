---
name: oke-cluster-upgrade
description: Upgrade OKE cluster Kubernetes version including control-plane, data-plane (node pools configuration), and rolling out changes to worker nodes. Use when upgrading an OKE cluster to a newer Kubernetes version.
metadata:
  version: "2.0"
  category: "devops"
---

# OKE Cluster Kubernetes Version Upgrade

This skill guides you through upgrading an Oracle Kubernetes Engine (OKE) cluster's Kubernetes version. The upgrade process involves three phases: control-plane upgrade, data-plane (node pool configuration) upgrade, and worker node rollout.

## User Approval Requirements

**CRITICAL: This workflow contains mutating operations that require explicit user approval.**

| Operation Type | CLI Command | Approval Required |
|---------------|-------------|-------------------|
| Read-only | `make oke-version-report` | No |
| **Control Plane Upgrade** | `make oke-upgrade` | **YES - MUST WAIT** |
| **Node Pool Config Upgrade** | `make oke-upgrade-node-pools` | **YES - MUST WAIT** |
| **Worker Node Cycling** | `make oke-node-cycle` | **YES - MUST WAIT** |

**Rules:**
- Always dry-run (`DRY_RUN=true`) before any mutation
- Present dry-run results and ask for explicit user approval
- Only execute (without DRY_RUN) after user confirms with "yes"
- Get separate approval for EACH phase

## Prerequisites

Before starting, gather the following information from the user:
- **PROJECT**: Project name (e.g., 'project-alpha', 'project-beta')
- **STAGE**: Environment stage (e.g., 'dev', 'staging', 'prod')
- **TARGET_VERSION** (optional): Specific Kubernetes version to upgrade to

## Upgrade Procedure

### Phase 1: Discovery and Planning (No Approval Needed)

1. **Generate version report** to see all clusters and available upgrades:
   ```bash
   make oke-version-report PROJECT=<project> STAGE=<stage>
   ```
   - Output: `reports/oke_versions_<project>_<stage>.html`
   - Review the HTML report to identify:
     - Clusters with available upgrades
     - Current Kubernetes versions
     - Node pool versions

2. **Decision Point - Version Selection**:
   - If user specified a target version, verify it exists in available upgrades
   - If no target specified, recommend the latest version from available upgrades
   - If no upgrades available, inform user cluster is at latest version

### Phase 2: Control-Plane Upgrade

3. **Dry-run the control-plane upgrade**:
   ```bash
   make oke-upgrade REPORT=reports/oke_versions_<project>_<stage>.html DRY_RUN=true
   ```
   - Review the dry-run output to confirm the upgrade path
   - Note which clusters will be upgraded

4. **APPROVAL CHECKPOINT - Control Plane Upgrade**:
   Present to user and WAIT for approval:
   ```
   Ready to upgrade cluster control plane(s):
   - Cluster: <cluster_name>
   - Current version: <current_version>
   - Target version: <target_version>
   - Impact: Kubernetes API will be briefly unavailable during upgrade
   - Duration: Typically 10-20 minutes

   Do you approve this control-plane upgrade? (yes/no)
   ```
   **DO NOT PROCEED until user responds "yes"**

5. **Execute control-plane upgrade** (only after approval):
   ```bash
   make oke-upgrade REPORT=reports/oke_versions_<project>_<stage>.html
   ```
   - Record the work_request_id(s) returned
   - Inform user: "Control-plane upgrade initiated."

6. **Wait for control-plane upgrade completion**:
   - Regenerate the version report to check status:
     ```bash
     make oke-version-report PROJECT=<project> STAGE=<stage>
     ```
   - Proceed to Phase 3 only when cluster shows new version and no available upgrades

### Phase 3: Data-Plane (Node Pool Configuration) Upgrade

7. **Dry-run node pool configuration upgrade**:
   ```bash
   make oke-upgrade-node-pools REPORT=reports/oke_versions_<project>_<stage>.html DRY_RUN=true
   ```
   - Review which node pools will be upgraded
   - Note version changes for each pool

8. **APPROVAL CHECKPOINT - Node Pool Config**:
   Present to user and WAIT for approval:
   ```
   Ready to upgrade node pool configuration(s):
   - Node Pool: <node_pool_name>
   - Target version: <target_version>
   - Impact: Configuration change only; running nodes not yet affected

   Do you approve this node pool configuration upgrade? (yes/no)
   ```
   **DO NOT PROCEED until user responds "yes"**

9. **Execute node pool configuration upgrade** (only after approval):
   ```bash
   make oke-upgrade-node-pools REPORT=reports/oke_versions_<project>_<stage>.html
   ```
   - This updates the node pool configuration but does NOT update running nodes

### Phase 4: Worker Node Rollout (Node Cycling)

10. **Dry-run the cycle operation**:
    ```bash
    make oke-node-cycle REPORT=reports/oke_versions_<project>_<stage>.html DRY_RUN=true
    ```
    - Review node count and cycling parameters

11. **APPROVAL CHECKPOINT - Node Cycling**:
    Present to user and WAIT for approval:
    ```
    Ready to cycle worker nodes (rolling replacement):
    - Node Pool: <node_pool_name>
    - Nodes to cycle: <node_count>
    - Impact: Pods will be evicted and rescheduled during node replacement
    - Duration: Depends on node count and drain time

    Do you approve cycling this node pool? (yes/no)
    ```
    **DO NOT PROCEED until user responds "yes"**

12. **Execute node cycling** (only after approval):
    ```bash
    make oke-node-cycle REPORT=reports/oke_versions_<project>_<stage>.html
    ```
    - This replaces boot volumes on worker nodes to apply the new version

13. **Verify completion**:
    - Regenerate version report:
      ```bash
      make oke-version-report PROJECT=<project> STAGE=<stage>
      ```
    - Confirm all components show the new version

## CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `make oke-version-report PROJECT=x STAGE=y` | Generate HTML report |
| `make oke-upgrade REPORT=path DRY_RUN=true` | Preview control plane upgrade |
| `make oke-upgrade REPORT=path` | Execute control plane upgrade |
| `make oke-upgrade-node-pools REPORT=path DRY_RUN=true` | Preview node pool config upgrade |
| `make oke-upgrade-node-pools REPORT=path` | Execute node pool config upgrade |
| `make oke-node-cycle REPORT=path DRY_RUN=true` | Preview node cycling |
| `make oke-node-cycle REPORT=path` | Execute node cycling |

## Error Handling

- **Cluster not ACTIVE**: Wait for any pending operations to complete
- **Version not available**: Check if cluster is already at latest version
- **Node pool upgrade fails**: Check lifecycle_state; may need to resolve unhealthy nodes first
- **Cycling fails**: Review maximum_unavailable setting; ensure cluster has capacity

## Rollback Considerations

- Control-plane upgrades cannot be rolled back
- Node pool configuration can be reverted, but nodes already cycled will remain on new version
- Always test in dev/staging before production upgrades

## Summary Report

After completion, provide a summary:
- Cluster name
- Previous version -> New version
- Number of node pools upgraded
- Number of nodes cycled
- Any warnings or issues encountered

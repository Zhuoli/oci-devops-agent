---
name: oke-cluster-upgrade
description: Upgrade OKE cluster Kubernetes version including control-plane, data-plane (node pools configuration), and rolling out changes to worker nodes. Use when upgrading an OKE cluster to a newer Kubernetes version.
metadata:
  version: "1.1"
  category: "devops"
---

# OKE Cluster Kubernetes Version Upgrade

This skill guides you through upgrading an Oracle Kubernetes Engine (OKE) cluster's Kubernetes version. The upgrade process involves three phases: control-plane upgrade, data-plane (node pool configuration) upgrade, and worker node rollout.

## User Approval Requirements

**CRITICAL: This workflow contains mutating operations that require explicit user approval.**

| Operation Type | Tools | Approval Required |
|---------------|-------|-------------------|
| Read-only | `list_oke_clusters`, `get_oke_cluster_details`, `list_node_pools` | No |
| **Mutating** | `upgrade_oke_cluster`, `upgrade_node_pool`, `cycle_node_pool` | **YES - MUST WAIT** |

**Rules:**
- Always dry-run (`dry_run=true`) before any mutation
- Present dry-run results and ask for explicit user approval
- Only execute (`dry_run=false`) after user confirms with "yes"
- Get separate approval for EACH mutating operation

## Prerequisites

Before starting, gather the following information from the user:
- **project**: Project name (e.g., 'project-alpha', 'project-beta')
- **stage**: Environment stage (e.g., 'dev', 'staging', 'prod')
- **region**: OCI region (e.g., 'us-phoenix-1', 'us-ashburn-1')
- **target_version** (optional): Specific Kubernetes version to upgrade to

## Upgrade Procedure

### Phase 1: Discovery and Planning (No Approval Needed)

1. **List available clusters** using `list_oke_clusters`:
   ```
   list_oke_clusters(project, stage, region)
   ```
   - Review the cluster list and identify the target cluster
   - Note the `cluster_id` for subsequent operations

2. **Get cluster details** using `get_oke_cluster_details`:
   ```
   get_oke_cluster_details(project, stage, region, cluster_id)
   ```
   - Check `kubernetes_version` - current version
   - Check `available_upgrades` - list of versions you can upgrade to
   - Check `lifecycle_state` - must be ACTIVE to proceed
   - Note all `node_pools` and their current versions

3. **Decision Point - Version Selection**:
   - If user specified a target version, verify it exists in `available_upgrades`
   - If no target specified, recommend the latest version from `available_upgrades`
   - If `available_upgrades` is empty, inform user no upgrade is available

### Phase 2: Control-Plane Upgrade

4. **Dry-run the control-plane upgrade**:
   ```
   upgrade_oke_cluster(project, stage, region, cluster_id, target_version, dry_run=True)
   ```
   - Review the dry-run output to confirm the upgrade path

5. **🛑 APPROVAL CHECKPOINT - Control Plane Upgrade**:
   Present to user and WAIT for approval:
   ```
   I'm ready to upgrade the cluster control plane:
   - Cluster: {cluster_name} ({cluster_id})
   - Current version: {current_version}
   - Target version: {target_version}
   - Impact: Kubernetes API will be briefly unavailable during upgrade
   - Duration: Typically 10-20 minutes

   Do you approve this control-plane upgrade? (yes/no)
   ```
   **DO NOT PROCEED until user responds "yes"**

6. **Execute control-plane upgrade** (only after approval):
   ```
   upgrade_oke_cluster(project, stage, region, cluster_id, target_version, dry_run=False)
   ```
   - Record the `work_request_id` returned
   - Inform user: "Control-plane upgrade initiated. Work request: {work_request_id}"

7. **Wait for control-plane upgrade completion**:
   - The cluster will show lifecycle_state=UPDATING during upgrade
   - Periodically check status with `get_oke_cluster_details`
   - Proceed to Phase 3 only when lifecycle_state returns to ACTIVE

### Phase 3: Data-Plane (Node Pool Configuration) Upgrade

8. **List node pools** to get current state:
   ```
   list_node_pools(project, stage, region, cluster_id)
   ```
   - Identify node pools where `kubernetes_version` < cluster's new version
   - Record each `node_pool_id` that needs upgrading

9. **For each node pool requiring upgrade**:

   a. **Dry-run node pool upgrade**:
   ```
   upgrade_node_pool(project, stage, region, node_pool_id, target_version, dry_run=True)
   ```

   b. **🛑 APPROVAL CHECKPOINT - Node Pool Config**:
   Present to user and WAIT for approval:
   ```
   Ready to upgrade node pool configuration:
   - Node Pool: {node_pool_name} ({node_pool_id})
   - Target version: {target_version}
   - Impact: Configuration change only; nodes not yet affected

   Do you approve this node pool configuration upgrade? (yes/no)
   ```
   **DO NOT PROCEED until user responds "yes"**

   c. **Execute node pool configuration upgrade** (only after approval):
   ```
   upgrade_node_pool(project, stage, region, node_pool_id, target_version, dry_run=False)
   ```
   - Record the `work_request_id`
   - This updates the node pool configuration but does NOT update running nodes

### Phase 4: Worker Node Rollout (Node Cycling)

10. **For each upgraded node pool, cycle the workers**:

    a. **Dry-run the cycle operation**:
    ```
    cycle_node_pool(project, stage, region, node_pool_id, maximum_unavailable=1, dry_run=True)
    ```
    - Review node count and cycling parameters

    b. **🛑 APPROVAL CHECKPOINT - Node Cycling**:
    Present to user and WAIT for approval:
    ```
    Ready to cycle worker nodes (rolling replacement):
    - Node Pool: {node_pool_name}
    - Nodes to cycle: {node_count}
    - Maximum unavailable: 1
    - Impact: Pods will be evicted and rescheduled during node replacement

    Do you approve cycling this node pool? (yes/no)
    ```
    **DO NOT PROCEED until user responds "yes"**

    c. **Execute node cycling** (only after approval):
    ```
    cycle_node_pool(project, stage, region, node_pool_id, maximum_unavailable=1, dry_run=False)
    ```
    - Record the `work_request_id`
    - This replaces boot volumes on worker nodes to apply the new version
    - **Production tip**: Use `maximum_unavailable=1` for minimal disruption

11. **Verify completion**:
    - Use `get_oke_cluster_details` to verify all components show the new version
    - Confirm all node pools are ACTIVE and running the target version

## Error Handling

- **Cluster not ACTIVE**: Wait for any pending operations to complete
- **Version not in available_upgrades**: Check if a newer version exists or if cluster is already at latest
- **Node pool upgrade fails**: Check node pool lifecycle_state; may need to resolve unhealthy nodes first
- **Cycling fails**: Review maximum_unavailable setting; ensure cluster has capacity

## Rollback Considerations

- Control-plane upgrades cannot be rolled back
- Node pool configuration can be reverted, but nodes already cycled will remain on new version
- Always test in dev/staging before production upgrades

## Summary Report

After completion, provide a summary:
- Cluster name and ID
- Previous version -> New version
- Number of node pools upgraded
- Number of nodes cycled
- Total work requests generated
- Any warnings or issues encountered

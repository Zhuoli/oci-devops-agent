---
name: oke-node-upgrade
description: Upgrade OKE node pools to latest node image version and cycle workers to apply new images. Use for regular node image maintenance, security patches, or OS updates without changing Kubernetes version.
metadata:
  version: "1.1"
  category: "devops"
---

# OKE Node Image Upgrade

This skill guides you through upgrading Oracle Kubernetes Engine (OKE) node pools to the latest node image version. This is used for applying security patches, OS updates, or newer Oracle Linux images without changing the Kubernetes version.

## User Approval Requirements

**CRITICAL: This workflow contains mutating operations that require explicit user approval.**

| Operation Type | Tools | Approval Required |
|---------------|-------|-------------------|
| Read-only | `list_oke_clusters`, `get_oke_cluster_details`, `list_node_pools`, `get_oke_version_report` | No |
| **Mutating** | `cycle_node_pool` | **YES - MUST WAIT** |

**Rules:**
- Always dry-run (`dry_run=true`) before any mutation
- Present dry-run results and ask for explicit user approval
- Only execute (`dry_run=false`) after user confirms with "yes"
- Get separate approval for EACH node pool cycling operation

## When to Use This Skill

- Apply security patches to worker nodes
- Update to newer Oracle Linux images
- Refresh node boot volumes with latest configurations
- Regular maintenance of node pool images

## Prerequisites

Before starting, gather the following information from the user:
- **project**: Project name (e.g., 'project-alpha', 'project-beta')
- **stage**: Environment stage (e.g., 'dev', 'staging', 'prod')
- **region**: OCI region (e.g., 'us-phoenix-1', 'us-ashburn-1')
- **cluster_id** (optional): Specific cluster OCID if known
- **node_pool_id** (optional): Specific node pool OCID if targeting a single pool
- **maximum_unavailable** (optional): Max nodes unavailable during cycling (default: 1)
- **maximum_surge** (optional): Max additional nodes during cycling

## Upgrade Procedure

### Phase 1: Discovery and Assessment (No Approval Needed)

1. **List clusters** to find the target:
   ```
   list_oke_clusters(project, stage, region)
   ```
   - Identify the cluster(s) requiring node image updates
   - Note the `cluster_id` for each

2. **Get cluster details** for each cluster:
   ```
   get_oke_cluster_details(project, stage, region, cluster_id)
   ```
   - Review all node pools and their current state
   - Note `lifecycle_state` - must be ACTIVE to proceed
   - Record `node_pool_id` for each pool needing updates

3. **Alternatively, list node pools directly**:
   ```
   list_node_pools(project, stage, region, cluster_id)
   ```
   - Get detailed node pool information
   - Identify pools by name pattern or specific IDs

### Phase 2: Node Pool Image Update Planning

4. **Decision Point - Scope Selection**:
   - **All node pools**: Cycle all pools in the cluster sequentially
   - **Specific pools**: Target only named pools (e.g., by pattern matching)
   - **Single pool**: Update one specific pool
   - Present the plan to the user for confirmation

5. **Determine cycling parameters**:
   - `maximum_unavailable`: How many nodes can be down simultaneously
     - Production: Use `1` for minimal disruption
     - Dev/Test: Can use higher values for faster rollout
   - `maximum_surge`: Additional nodes created during rolling update
     - Set this if you want extra capacity during updates
     - Leave unset if cluster has limited capacity

### Phase 3: Execute Node Cycling

6. **For each node pool to update**:

   a. **Dry-run the cycle operation**:
   ```
   cycle_node_pool(
     project, stage, region,
     node_pool_id,
     maximum_unavailable=1,
     dry_run=True
   )
   ```
   - Review output: node count, pool name, cycling parameters

   b. **🛑 APPROVAL CHECKPOINT - Node Cycling**:
   Present to user and WAIT for approval:
   ```
   Ready to cycle worker nodes to apply new image:
   - Node Pool: {node_pool_name} ({node_pool_id})
   - Current nodes: {node_count}
   - Maximum unavailable: {maximum_unavailable}
   - Maximum surge: {maximum_surge or "not set"}
   - Impact: Each node will be:
     1. Cordoned (no new pods scheduled)
     2. Drained (existing pods evicted)
     3. Terminated
     4. Replaced with new node using latest image

   Do you approve cycling this node pool? (yes/no)
   ```
   **DO NOT PROCEED until user responds "yes"**

   c. **Execute node cycling** (only after approval):
   ```
   cycle_node_pool(
     project, stage, region,
     node_pool_id,
     maximum_unavailable=1,
     maximum_surge=<optional>,
     dry_run=False
   )
   ```
   - Record the `work_request_id` returned
   - Inform user: "Node pool cycling initiated for {pool_name}. Work request: {work_request_id}"

7. **Processing Order Recommendations**:
   - **Sequential processing (recommended for production)**:
     - Process one node pool at a time
     - Wait for each to complete before starting the next
     - Get approval for each pool individually
     - Provides controlled rollout and easy rollback points

   - **Parallel processing (acceptable for dev/test)**:
     - Still requires individual approval for each pool
     - Can initiate multiple cycles after getting separate approvals
     - Faster but higher risk of service disruption

### Phase 4: Verification (No Approval Needed)

8. **Monitor progress**:
   - Node pools will show `lifecycle_state=UPDATING` during cycling
   - Periodically check with `get_oke_cluster_details` or `list_node_pools`
   - Each node is:
     1. Cordoned (no new pods scheduled)
     2. Drained (existing pods evicted)
     3. Terminated
     4. Replaced with new node using latest image

9. **Verify completion**:
   ```
   get_oke_cluster_details(project, stage, region, cluster_id)
   ```
   - Confirm all node pools are ACTIVE
   - Verify node counts match expected values

## Multi-Cluster Operations

For upgrading nodes across multiple clusters in a stage:

1. **Generate version report**:
   ```
   get_oke_version_report(project, stage)
   ```
   - Review all clusters and their node pools
   - Identify which need image updates

2. **Process clusters sequentially**:
   - Complete one cluster before moving to next
   - Get approval for each node pool in each cluster
   - Provides clear rollback boundaries

## Error Handling

- **Node pool not ACTIVE**: Wait for pending operations; check for failed nodes
- **Insufficient capacity**: Reduce `maximum_unavailable` or add `maximum_surge`
- **Pods fail to evict**: Check for PodDisruptionBudgets blocking eviction
- **Cycling takes too long**: Large pools or slow pod termination; be patient

## Production Best Practices

1. **Timing**: Schedule during maintenance windows
2. **Communication**: Notify stakeholders before starting
3. **Monitoring**: Watch application health during rollout
4. **Capacity**: Ensure sufficient cluster capacity for surge
5. **Rollback plan**: Know how to pause or stop cycling if issues arise

## Parameters Reference

| Parameter | Description | Recommended Values |
|-----------|-------------|-------------------|
| `maximum_unavailable` | Max nodes down at once | Prod: 1, Dev: 2-3 |
| `maximum_surge` | Extra nodes during update | 0-1 typically |

## Summary Report

After completion, provide a summary:
- Cluster name and ID
- Number of node pools processed
- Total nodes cycled
- Work requests generated
- Processing time (if tracked)
- Any warnings or issues encountered
- Pools skipped or deferred (if any)

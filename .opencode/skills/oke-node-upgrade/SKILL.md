---
name: oke-node-upgrade
description: Upgrade OKE node pools to latest node image version and cycle workers to apply new images. Use for OS host patching, regular node image maintenance, security patches, or OS updates without changing Kubernetes version.
metadata:
  version: "2.0"
  category: "devops"
---

# OKE Node Image Upgrade

This skill guides you through upgrading Oracle Kubernetes Engine (OKE) node pools to the latest node image version. This is used for applying security patches, OS updates, or newer Oracle Linux images without changing the Kubernetes version.

## User Approval Requirements

**CRITICAL: This workflow contains mutating operations that require explicit user approval.**

| Operation Type | CLI Command | Approval Required |
|---------------|-------------|-------------------|
| Read-only | `make oke-version-report`, `make image-updates` | No |
| **Image Bump** | `make oke-node-pool-bump` | **YES - MUST WAIT** |
| **Node Cycling** | `make oke-node-cycle` | **YES - MUST WAIT** |

**Rules:**
- Always dry-run (`DRY_RUN=true`) before any mutation
- Present dry-run results and ask for explicit user approval
- Only execute (without DRY_RUN) after user confirms with "yes"
- Get separate approval for EACH mutating operation

## When to Use This Skill

- Do OS host patch / host patching on worker nodes
- Apply security patches to worker nodes
- Update to newer Oracle Linux images
- Refresh node boot volumes with latest configurations
- Regular maintenance of node pool images

## Prerequisites

Before starting, gather the following information from the user:
- **PROJECT**: Project name (e.g., 'project-alpha', 'project-beta')
- **STAGE**: Environment stage (e.g., 'dev', 'staging', 'prod')

## Upgrade Procedure

### Phase 1: Discovery and Assessment (No Approval Needed)

1. **Check for available image updates**:
   ```bash
   make image-updates PROJECT=<project> STAGE=<stage>
   ```
   - Output: Console table + `oci_image_updates_report.csv`
   - Review instances with newer images available
   - Note which nodes need patching

2. **Alternatively, generate version report** for cluster overview:
   ```bash
   make oke-version-report PROJECT=<project> STAGE=<stage>
   ```
   - Output: `reports/oke_versions_<project>_<stage>.html`
   - Review all clusters and node pools

3. **Decision Point - Scope Selection**:
   - **All node pools**: Process all pools with updates available
   - **Specific pools**: Target only certain pools by filtering the CSV
   - Present the plan to the user for confirmation

### Phase 2: Node Pool Image Update

**Option A: Using CSV-based image bump (recommended)**

4. **Dry-run the image bump**:
   ```bash
   make oke-node-pool-bump CSV=oci_image_updates_report.csv DRY_RUN=true
   ```
   - Review which node pools will be updated
   - Note current vs new image for each

5. **APPROVAL CHECKPOINT - Image Bump**:
   Present to user and WAIT for approval:
   ```
   Ready to update node pool images:
   - Node Pool: <node_pool_name>
   - Current Image: <current_image>
   - New Image: <new_image>
   - Impact: Node pool configuration updated; nodes not yet affected

   Do you approve this image update? (yes/no)
   ```
   **DO NOT PROCEED until user responds "yes"**

6. **Execute image bump** (only after approval):
   ```bash
   make oke-node-pool-bump CSV=oci_image_updates_report.csv
   ```
   - This updates node pool images and initiates cycling

**Option B: Using version report for node cycling only**

If images are already updated in node pool config, skip to Phase 3.

### Phase 3: Execute Node Cycling

7. **Dry-run the cycle operation**:
   ```bash
   make oke-node-cycle REPORT=reports/oke_versions_<project>_<stage>.html DRY_RUN=true
   ```
   - Review node count and cycling parameters

8. **APPROVAL CHECKPOINT - Node Cycling**:
   Present to user and WAIT for approval:
   ```
   Ready to cycle worker nodes to apply new image:
   - Node Pool: <node_pool_name>
   - Nodes to cycle: <node_count>
   - Impact: Each node will be:
     1. Cordoned (no new pods scheduled)
     2. Drained (existing pods evicted)
     3. Terminated
     4. Replaced with new node using latest image

   Do you approve cycling this node pool? (yes/no)
   ```
   **DO NOT PROCEED until user responds "yes"**

9. **Execute node cycling** (only after approval):
   ```bash
   make oke-node-cycle REPORT=reports/oke_versions_<project>_<stage>.html
   ```
   - Record work_request_id(s) returned
   - Monitor progress

### Phase 4: Verification (No Approval Needed)

10. **Verify completion**:
    - Re-run image updates check:
      ```bash
      make image-updates PROJECT=<project> STAGE=<stage>
      ```
    - Confirm no updates available (all nodes patched)
    - Or regenerate version report to verify status

## CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `make image-updates PROJECT=x STAGE=y` | Check for available image updates |
| `make oke-version-report PROJECT=x STAGE=y` | Generate HTML version report |
| `make oke-node-pool-bump CSV=path DRY_RUN=true` | Preview image bump |
| `make oke-node-pool-bump CSV=path` | Execute image bump |
| `make oke-node-cycle REPORT=path DRY_RUN=true` | Preview node cycling |
| `make oke-node-cycle REPORT=path` | Execute node cycling |

## Processing Order Recommendations

- **Sequential processing (recommended for production)**:
  - Process one node pool at a time
  - Wait for each to complete before starting the next
  - Get approval for each pool individually
  - Provides controlled rollout and easy rollback points

- **Parallel processing (acceptable for dev/test)**:
  - Can initiate multiple cycles after getting separate approvals
  - Faster but higher risk of service disruption

## Error Handling

- **Node pool not ACTIVE**: Wait for pending operations; check for failed nodes
- **Insufficient capacity**: Reduce maximum_unavailable or add maximum_surge
- **Pods fail to evict**: Check for PodDisruptionBudgets blocking eviction
- **Cycling takes too long**: Large pools or slow pod termination; be patient

## Production Best Practices

1. **Timing**: Schedule during maintenance windows
2. **Communication**: Notify stakeholders before starting
3. **Monitoring**: Watch application health during rollout
4. **Capacity**: Ensure sufficient cluster capacity for surge
5. **Rollback plan**: Know how to pause or stop cycling if issues arise

## Summary Report

After completion, provide a summary:
- Cluster name(s) processed
- Number of node pools updated
- Total nodes cycled
- Previous image -> New image
- Processing time (if tracked)
- Any warnings or issues encountered

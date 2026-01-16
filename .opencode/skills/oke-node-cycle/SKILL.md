---
name: oke-node-cycle
description: Cycle OKE node pool workers to apply new images or Kubernetes versions by replacing boot volumes. Use for OS patching, applying security updates, or completing Kubernetes version upgrades on worker nodes.
metadata:
  version: "1.0"
  category: "devops"
---

# OKE Node Pool Cycling

Cycle node pool workers by replacing their boot volumes to apply new images, security patches, or Kubernetes version upgrades to running nodes.

## User Approval Requirements

**CRITICAL: This skill performs mutating operations that require explicit user approval.**

| Operation | Approval Required |
|-----------|-------------------|
| Dry-run (preview) | No |
| **Actual cycling** | **YES - MUST WAIT FOR USER CONFIRMATION** |

## When to Use This Skill

- "Cycle the node pools"
- "Apply OS patches to nodes"
- "Do host patching"
- "Roll out the new node images"
- "Refresh the worker nodes"
- After node pool configuration upgrade (oke-upgrade-node-pools)

## Prerequisites

- **REPORT**: Path to HTML report from oke-version-report

Optional parameters:
- **GRACE_PERIOD**: Time for pods to drain gracefully (default: PT30M = 30 minutes)
- **FORCE_AFTER_GRACE**: Force eviction after grace period expires

## CLI Tool Reference

### Command
```bash
# Dry-run first (always do this)
make oke-node-cycle REPORT=<path> DRY_RUN=true

# Actual cycling (only after user approval)
make oke-node-cycle REPORT=<path> [GRACE_PERIOD=PT30M] [FORCE_AFTER_GRACE=true]
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| REPORT | Yes | Path to HTML report | reports/oke_versions.html |
| GRACE_PERIOD | No | Pod drain timeout (ISO 8601 duration, default: PT30M) | PT30M |
| FORCE_AFTER_GRACE | No | Force evict pods after grace period | true |
| DRY_RUN | No | Preview only | true |
| VERBOSE | No | Detailed output | true |

### Output Format

**Console output** showing:
- Node pools being cycled
- Number of nodes affected per pool
- Work request IDs for each cycling operation
- Progress and status updates

### Output Interpretation

- Nodes are processed in rolling fashion based on pool settings
- Only `maximum_unavailable` nodes are down at any time
- Process: cordon -> drain -> terminate -> replace with new node
- Watch for pod disruption budget (PDB) violations in output

## Procedure

1. **Always dry-run first**:
   ```bash
   make oke-node-cycle REPORT=<path> DRY_RUN=true
   ```

2. **Review the dry-run output** and present to user:
   ```
   The following node pools will be cycled:
   - Cluster: <cluster_name>
     - Node Pool: <pool_name>
       - Nodes to cycle: <count>
       - Maximum unavailable: <number>
   ```

3. **APPROVAL CHECKPOINT**:
   ```
   Ready to cycle worker nodes:
   - Node Pool: <name>
   - Nodes to cycle: <count>
   - Grace period: 30 minutes

   Impact: Each node will be:
   1. Cordoned (no new pods scheduled)
   2. Drained (existing pods evicted to other nodes)
   3. Terminated
   4. Replaced with new node using latest image

   This is a rolling operation - only <maximum_unavailable> nodes will be
   unavailable at any time.

   Do you approve cycling this node pool? (yes/no)
   ```

   **DO NOT PROCEED until user explicitly responds "yes"**

4. **Execute** (only after approval):
   ```bash
   make oke-node-cycle REPORT=<path>
   ```

5. **Monitor and report progress**:
   - Work request IDs for tracking
   - Expected duration based on node count
   - Any warnings or errors

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Pods fail to evict | PodDisruptionBudget blocking | Check PDB settings, may need to adjust or use FORCE_AFTER_GRACE |
| Cycling takes too long | Large pools or slow termination | Be patient, check OCI Console for work request status |
| Insufficient capacity | Can't provision replacement | Reduce maximum_unavailable or wait for capacity |
| Node stuck terminating | OCI infrastructure issue | Check work request in OCI Console |

## Summary Report

After execution, report:
- Number of node pools cycled
- Total nodes replaced
- Work request IDs for tracking
- Any errors or warnings encountered
- Time to complete (if finished)

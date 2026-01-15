---
name: delete-oke-cluster
description: Delete an OKE cluster from Oracle Cloud Infrastructure. Use with extreme caution - this permanently deletes the cluster and optionally its node pools. Only use when user explicitly requests cluster deletion.
metadata:
  version: "1.0"
  category: "resource-management"
---

# Delete OKE Cluster

Delete an Oracle Kubernetes Engine cluster from Oracle Cloud Infrastructure.

## User Approval Requirements

**CRITICAL: This is a DESTRUCTIVE operation that requires explicit user approval.**

| Operation | Approval Required |
|-----------|-------------------|
| **Delete cluster** | **YES - MUST CONFIRM EXPLICITLY** |

## When to Use This Skill

- "Delete this OKE cluster"
- "Remove the Kubernetes cluster"
- **ONLY when user explicitly requests cluster deletion**

## Prerequisites

Gather from the user:
- **PROJECT**: Project name
- **STAGE**: Environment stage
- **REGION**: OCI region where the cluster exists
- **CLUSTER_ID**: Cluster OCID (starts with `ocid1.cluster...`)
- **SKIP_NODE_POOLS** (optional): Set to `true` to keep node pools

## CLI Tool Reference

### Command
```bash
make delete-oke-cluster PROJECT=<project> STAGE=<stage> REGION=<region> CLUSTER_ID=<ocid> [SKIP_NODE_POOLS=true]
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| PROJECT | Yes | Project name | my-project |
| STAGE | Yes | Environment stage | dev |
| REGION | Yes | OCI region | us-phoenix-1 |
| CLUSTER_ID | Yes | Cluster OCID | ocid1.cluster.oc1.phx.xxx |
| SKIP_NODE_POOLS | No | Skip deleting node pools | true |

### Output Format

**Console output** showing:
- Node pool deletion progress (unless skipped)
- Cluster deletion work request ID
- Final status

## Procedure

1. **Get cluster details first**
   - Use oke-version-report skill to verify cluster info:
     ```bash
     make oke-version-report PROJECT=<project> STAGE=<stage>
     ```
   - Confirm the cluster ID matches what user wants to delete

2. **Confirm the deletion** with the user:
   ```
   You are requesting to delete OKE cluster:
   - Cluster ID: <cluster_id>
   - Region: <region>
   - Project: <project>
   - Stage: <stage>

   WARNING: This operation will PERMANENTLY DELETE:
   - The Kubernetes control plane
   - All node pools (unless SKIP_NODE_POOLS=true)
   - All workloads running on the cluster
   - All Kubernetes resources (deployments, services, configmaps, etc.)

   This action CANNOT be undone.
   ```

3. **CRITICAL APPROVAL CHECKPOINT**:
   ```
   To confirm deletion, please type 'yes' to proceed.

   Do you want to delete OKE cluster '<cluster_id>'? (yes/no)
   ```

   **DO NOT PROCEED unless user explicitly types "yes"**

4. **Execute only after explicit confirmation**:
   ```bash
   make delete-oke-cluster PROJECT=<project> STAGE=<stage> REGION=<region> CLUSTER_ID=<cluster_id>
   ```

5. **Report result** to user

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Cluster not found | Wrong ID or region | Verify cluster OCID in OCI Console |
| Permission denied | Insufficient IAM policy | Check user's OCI permissions |
| Cluster in use | Active operations | Wait for operations to complete |
| Node pool deletion failed | Pool stuck | May need manual intervention in Console |

## Summary Report

After execution, report:
- Cluster deleted: `<cluster_id>`
- Region: `<region>`
- Node pools deleted: Yes/No
- Work request ID (for tracking)
- Status: Success/Failed

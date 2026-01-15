---
name: oke-version-report
description: Generate an HTML report showing all OKE clusters and node pools with their Kubernetes versions, available upgrades, and health status. Use when users ask about cluster versions, upgrade availability, or need a comprehensive OKE status overview.
metadata:
  version: "1.0"
  category: "devops"
---

# OKE Version Report

Generate a comprehensive HTML report of OKE cluster and node pool Kubernetes versions across all regions for a project/stage.

## User Approval Requirements

**All operations in this skill are read-only and do not require user approval.**

| Operation | Approval Required |
|-----------|-------------------|
| Generate version report | No |

## When to Use This Skill

- "What OKE clusters do we have?"
- "What Kubernetes versions are running?"
- "Are there any upgrades available?"
- "Generate a version report for staging"
- "Give me an OKE status overview"
- "Show me all clusters in prod"

## Prerequisites

Gather from the user:
- **PROJECT**: Project name (e.g., 'my-project')
- **STAGE**: Environment stage (e.g., 'dev', 'staging', 'prod')

## CLI Tool Reference

### Command
```bash
make oke-version-report PROJECT=<project> STAGE=<stage>
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| PROJECT | Yes | Project name from meta.yaml | my-project |
| STAGE | Yes | Environment stage | dev |

### Output Format

**HTML File:** `reports/oke_versions_<project>_<stage>.html`

The report contains a table with columns:
- Project, Stage, Region
- Cluster Name, Cluster OCID
- Cluster Version
- Available Upgrades (comma-separated list)
- Node Pool Name, Node Pool OCID
- Node Pool Version
- Compartment OCID

### Output Interpretation

1. **Available Upgrades column**: If not empty, the cluster can be upgraded to those versions
2. **Version mismatches**: If node pool version differs from cluster version, node pools need upgrade
3. **All regions included**: Report covers all regions configured for the project/stage in meta.yaml

## Procedure

1. **Execute the command**:
   ```bash
   make oke-version-report PROJECT=<project> STAGE=<stage>
   ```

2. **Wait for completion**: The tool scans all regions in parallel (may take 1-2 minutes)

3. **Locate the output file**: `reports/oke_versions_<project>_<stage>.html`

4. **Read and summarize the report** for the user:
   - Total number of clusters found
   - Clusters with available upgrades (list names and versions)
   - Node pools with version mismatches
   - Any regions with errors

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No clusters found | Empty compartments or wrong config | Verify compartment IDs in meta.yaml |
| Authentication error | Expired session token | Run `oci session authenticate --profile-name DEFAULT --region <region>` |
| Region not accessible | Missing IAM permissions | Check user policies in OCI Console |

## Summary Report

Present to the user:
- Report file location: `reports/oke_versions_<project>_<stage>.html`
- Total clusters discovered
- Clusters requiring upgrades (list names and available versions)
- Node pools with version mismatches
- Recommended next steps (e.g., "Use the oke-upgrade skill to upgrade cluster X")

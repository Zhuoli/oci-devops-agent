---
name: image-updates
description: Check for newer OS images available for compute instances and OKE node pools. Generates a CSV report showing which instances have image updates available.
metadata:
  version: "1.0"
  category: "devops"
---

# Image Updates Check

Check for newer operating system images for compute instances and generate a CSV report.

## User Approval Requirements

**All operations in this skill are read-only and do not require user approval.**

| Operation | Approval Required |
|-----------|-------------------|
| Check for image updates | No |

## When to Use This Skill

- "Check for image updates"
- "Are there OS patches available?"
- "Which nodes need patching?"
- "Check host patch status"
- "What images are outdated?"

## Prerequisites

Gather from the user:
- **PROJECT**: Project name (e.g., 'my-project')
- **STAGE**: Environment stage (e.g., 'dev', 'staging', 'prod')

## CLI Tool Reference

### Command
```bash
make image-updates PROJECT=<project> STAGE=<stage>
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| PROJECT | Yes | Project name | my-project |
| STAGE | Yes | Environment stage | dev |

### Output Format

**CSV File:** `oci_image_updates_report.csv`

Columns:
- `host_name`: Instance display name
- `region`: OCI region
- `compartment_id`: Compartment OCID
- `current_image`: Current image name
- `new_image_name`: Newer available image name

**Console output**: Rich formatted table with summary

### Output Interpretation

- Rows in the CSV indicate instances with newer images available
- Empty CSV (header only) means all instances are up-to-date
- Use the oke-node-pool-bump skill to apply updates from this CSV

## Procedure

1. **Execute the command**:
   ```bash
   make image-updates PROJECT=<project> STAGE=<stage>
   ```

2. **Wait for completion**: Tool scans all regions in parallel

3. **Review the console output**: Shows summary table

4. **Check the CSV file**: `oci_image_updates_report.csv`
   ```bash
   cat oci_image_updates_report.csv
   ```

5. **Report to user**:
   - Total instances checked
   - Number with updates available
   - List the instances needing updates
   - Recommend next steps

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No instances found | Empty compartments | Verify meta.yaml configuration |
| Image lookup failed | API error | Check OCI service status |
| Authentication error | Session expired | Run `oci session authenticate` |

## Summary Report

Present to the user:
- CSV file location: `oci_image_updates_report.csv`
- Total instances checked
- Instances with updates available (list names)
- Current vs available image versions
- **Next step**: "Use the oke-node-pool-bump skill to apply these updates"

---
name: delete-bucket
description: Delete an OCI Object Storage bucket. Use with extreme caution - this permanently deletes the bucket and all its contents. Only use when user explicitly requests bucket deletion.
metadata:
  version: "1.0"
  category: "resource-management"
---

# Delete OCI Bucket

Delete an Object Storage bucket from Oracle Cloud Infrastructure.

## User Approval Requirements

**CRITICAL: This is a DESTRUCTIVE operation that requires explicit user approval.**

| Operation | Approval Required |
|-----------|-------------------|
| **Delete bucket** | **YES - MUST CONFIRM EXPLICITLY** |

## When to Use This Skill

- "Delete this bucket"
- "Remove the object storage bucket"
- **ONLY when user explicitly requests bucket deletion**

## Prerequisites

Gather from the user:
- **PROJECT**: Project name
- **STAGE**: Environment stage
- **REGION**: OCI region where the bucket exists
- **BUCKET**: Exact bucket name to delete
- **NAMESPACE** (optional): Object storage namespace (auto-detected if not provided)

## CLI Tool Reference

### Command
```bash
make delete-bucket PROJECT=<project> STAGE=<stage> REGION=<region> BUCKET=<bucket> [NAMESPACE=<namespace>]
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| PROJECT | Yes | Project name | my-project |
| STAGE | Yes | Environment stage | dev |
| REGION | Yes | OCI region | us-phoenix-1 |
| BUCKET | Yes | Bucket name to delete | my-bucket |
| NAMESPACE | No | Object storage namespace | my-namespace |

### Output Format

**Console output** showing:
- Bucket deletion progress
- Object cleanup status (if bucket not empty)
- Final success/failure status

## Procedure

1. **Confirm the bucket details** with the user before proceeding:
   ```
   You are requesting to delete bucket: '<bucket>'
   Region: <region>
   Project: <project>
   Stage: <stage>

   WARNING: This operation will PERMANENTLY DELETE:
   - The bucket itself
   - ALL objects stored in the bucket
   - ALL object versions (if versioning enabled)

   This action CANNOT be undone. Data will be permanently lost.
   ```

2. **CRITICAL APPROVAL CHECKPOINT**:
   ```
   To confirm deletion, please type 'yes' to proceed.

   Do you want to delete bucket '<bucket>' and all its contents? (yes/no)
   ```

   **DO NOT PROCEED unless user explicitly types "yes"**

3. **Execute only after explicit confirmation**:
   ```bash
   make delete-bucket PROJECT=<project> STAGE=<stage> REGION=<region> BUCKET=<bucket>
   ```

4. **Report result** to user

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Bucket not found | Wrong name or region | Verify bucket name and region |
| Permission denied | Insufficient IAM policy | Check user's OCI permissions |
| Bucket not empty | Contains objects | Tool handles cleanup automatically |

## Summary Report

After execution, report:
- Bucket deleted: `<bucket_name>`
- Region: `<region>`
- Status: Success/Failed
- Any errors encountered

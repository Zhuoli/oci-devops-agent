---
name: ssh-sync
description: Generate SSH configuration for OCI instances including OKE worker nodes and ODO instances. Creates SSH config entries with ProxyCommand for bastion access.
metadata:
  version: "1.0"
  category: "infrastructure"
---

# SSH Sync

Generate SSH configuration for Oracle Cloud Infrastructure instances with automatic bastion proxy setup.

## User Approval Requirements

**All operations in this skill are read-only and do not require user approval.**

| Operation | Approval Required |
|-----------|-------------------|
| Generate SSH config | No |

## When to Use This Skill

- "Generate SSH config"
- "Sync SSH configuration"
- "Set up SSH access to instances"
- "Create SSH config for dev environment"
- "How do I SSH to the OKE nodes?"

## Prerequisites

Gather from the user:
- **PROJECT**: Project name (e.g., 'my-project')
- **STAGE**: Environment stage (e.g., 'dev', 'staging', 'prod')

## CLI Tool Reference

### Command
```bash
make ssh-sync PROJECT=<project> STAGE=<stage>
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| PROJECT | Yes | Project name | my-project |
| STAGE | Yes | Environment stage | dev |

### Output Format

**SSH Config File:** `ssh_configs/<project>_<stage>.txt`

Contains SSH config entries like:
```
Host node-abc123
  HostName 10.0.1.5
  User opc
  IdentityFile ~/.ssh/id_rsa
  ProxyCommand ssh -W %h:%p bastion-host
  StrictHostKeyChecking no
```

### Output Interpretation

The generated file contains:
- One Host entry per discovered instance
- ProxyCommand for accessing private instances via bastion
- Appropriate user (opc for Oracle Linux)
- IdentityFile paths

## Procedure

1. **Execute the command**:
   ```bash
   make ssh-sync PROJECT=<project> STAGE=<stage>
   ```

2. **Wait for completion**: Tool discovers instances across all regions

3. **Locate the output file**: `ssh_configs/<project>_<stage>.txt`

4. **Provide usage instructions** to the user:

   **Option A: Include in SSH config**
   ```bash
   # Add this line to ~/.ssh/config
   Include /path/to/oci-devops-agent/ssh_configs/<project>_<stage>.txt
   ```

   **Option B: Use directly**
   ```bash
   ssh -F ssh_configs/<project>_<stage>.txt <hostname>
   ```

5. **Report summary**:
   - Number of instances configured
   - File location
   - Usage instructions

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No instances found | Empty compartments | Verify meta.yaml configuration |
| No bastion found | Bastion not provisioned | Set up a bastion host in OCI |
| Authentication error | Session expired | Run `oci session authenticate` |

## Summary Report

Present to the user:
- Output file location: `ssh_configs/<project>_<stage>.txt`
- Number of instances configured
- Regions covered
- Instructions for using the config file

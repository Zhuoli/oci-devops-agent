---
name: ssh-help
description: Display help information about SSH sync configuration, prerequisites, and usage examples.
metadata:
  version: "1.0"
  category: "infrastructure"
---

# SSH Help

Display SSH sync configuration help and usage information.

## User Approval Requirements

**This skill is informational only - no operations performed.**

| Operation | Approval Required |
|-----------|-------------------|
| Display help | No |

## When to Use This Skill

- "How do I set up SSH?"
- "Show SSH help"
- "What are the SSH prerequisites?"
- "Help with SSH configuration"

## CLI Tool Reference

### Command
```bash
make ssh-help
```

### Output Format

**Console output** displaying:
- Configuration requirements
- Prerequisites (OCI CLI, SSH keys, profiles)
- Usage examples
- Output file locations
- Troubleshooting tips

## Procedure

1. **Run the help command**:
   ```bash
   make ssh-help
   ```

2. **Present the information** to the user

3. **If user needs to generate config**, direct them to the ssh-sync skill

## Summary

This is an informational skill - present the help output to the user and offer to run ssh-sync if they want to generate configuration.

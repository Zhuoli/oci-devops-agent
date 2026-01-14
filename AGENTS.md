# OCI DevOps Agent

**AI agents MUST use the MCP Server to interact with Oracle Cloud Infrastructure (OCI) resources.** Do not attempt to use OCI CLI or SDK directly - all OCI operations should go through the MCP tools provided by this server.

## Skills

Refer to `.opencode/skills/` for guided workflows on complex operations like OKE cluster upgrades, node pool cycling, and deployment troubleshooting.

## Usage Examples

```
User: What OKE clusters do we have in my-app dev?
Agent: Use MCP tools to list clusters in the specified project/stage/region.

User: Upgrade the OKE cluster to the latest version
Agent: Use MCP tools to check current version, find upgrade path, then upgrade
       with dry_run=true first. Get user approval before executing.

User: Did my last deployment succeed?
Agent: Use MCP tools to list DevOps projects, find the pipeline, and check
       recent deployment status.

User: Why did my deployment fail?
Agent: Use MCP tools to get deployment logs and analyze failed stages.

User: Are there node image updates available?
Agent: Use MCP tools to check for outdated node images across clusters.

User: Cycle the node pools to apply new images
Agent: Use MCP tools to cycle each node pool. Get user approval for each
       pool before executing.
```

## Safety

Mutating operations (upgrades, node cycling) require explicit user approval. Always dry-run first and get confirmation before making changes.

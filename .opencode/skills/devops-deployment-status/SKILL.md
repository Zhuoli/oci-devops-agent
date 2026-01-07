---
name: devops-deployment-status
description: Check OCI DevOps deployment pipeline status, view recent deployments, and troubleshoot failed deployments. Use when checking if a deployment succeeded, when it started, or diagnosing deployment failures.
metadata:
  version: "1.0"
  category: "devops"
---

# OCI DevOps Deployment Status

This skill guides you through checking OCI DevOps deployment pipeline status, viewing recent deployments, and troubleshooting failed deployments. All operations in this skill are read-only.

## User Approval Requirements

**All operations in this skill are read-only and do not require user approval.**

| Operation Type | Tools | Approval Required |
|---------------|-------|-------------------|
| Read-only | `list_devops_projects`, `list_deployment_pipelines`, `get_recent_deployment`, `get_deployment_logs` | No |

## When to Use This Skill

- Check if the most recent deployment succeeded or failed
- Find out when a deployment started and finished
- Diagnose why a deployment failed
- List all DevOps projects in a compartment
- List all deployment pipelines for a project
- Get detailed deployment execution logs

## Prerequisites

Before starting, gather the following information from the user:
- **project**: Project name from meta.yaml (e.g., 'project-alpha', 'project-beta')
- **stage**: Environment stage (e.g., 'dev', 'staging', 'prod')
- **region**: OCI region (e.g., 'us-phoenix-1', 'us-ashburn-1')

Optional (if user knows them):
- **devops_project_id**: Specific DevOps project OCID
- **pipeline_id**: Specific deployment pipeline OCID
- **deployment_id**: Specific deployment OCID

## Common Workflows

### Workflow 1: Check Recent Deployment Status

**Use case**: "Did my last deployment succeed?"

1. **If user knows the pipeline_id, skip to step 3**

2. **List DevOps projects** to find the target project:
   ```
   list_devops_projects(project, stage, region)
   ```
   - Review the list of DevOps projects
   - Note the `project_id` of the target project

3. **List deployment pipelines** for the project:
   ```
   list_deployment_pipelines(project, stage, region, devops_project_id)
   ```
   - Review the list of pipelines
   - Note the `pipeline_id` of the target pipeline

4. **Get the most recent deployment**:
   ```
   get_recent_deployment(project, stage, region, pipeline_id)
   ```
   - The response includes:
     - `status`: SUCCEEDED, FAILED, IN_PROGRESS, ACCEPTED, or CANCELED
     - `is_success`: Boolean indicating success
     - `is_failed`: Boolean indicating failure
     - `time_started`: When the deployment began
     - `time_finished`: When the deployment completed
     - `failed_stages`: List of stages that failed (if any)

5. **Report the status to user**:
   ```
   Most recent deployment for pipeline {pipeline_name}:
   - Status: {status}
   - Started: {time_started}
   - Finished: {time_finished}
   - Duration: {calculated_duration}
   ```

### Workflow 2: Diagnose Failed Deployment

**Use case**: "Why did my deployment fail?"

1. **Get recent deployment** (follow steps 1-4 from Workflow 1):
   ```
   get_recent_deployment(project, stage, region, pipeline_id)
   ```
   - Check if `is_failed` is true
   - Note the `deployment_id`
   - Review `failed_stages` for initial failure indication

2. **Get detailed deployment logs**:
   ```
   get_deployment_logs(project, stage, region, deployment_id)
   ```
   - The response includes:
     - `lifecycle_state`: Overall deployment state
     - `lifecycle_details`: Error message/reason for failure
     - `stages`: List of all stages with their status
     - `failed_stages`: Detailed info on failed stages
     - `summary`: Human-readable summary

3. **Analyze and report findings**:
   ```
   Deployment {deployment_id} failed:

   Summary: {summary}

   Failed Stage(s):
   - {stage_name}: {status}
     Error: {error_details}
     Started: {time_started}
     Failed at: {time_finished}

   Recommendation: {based on error type}
   ```

### Workflow 3: List All Projects and Pipelines

**Use case**: "What DevOps projects and pipelines do we have?"

1. **List all DevOps projects**:
   ```
   list_devops_projects(project, stage, region)
   ```
   - Present the list with project names and IDs

2. **For each project, list its pipelines**:
   ```
   list_deployment_pipelines(project, stage, region, devops_project_id)
   ```
   - Build a hierarchical view:
   ```
   DevOps Projects in {project}/{stage}/{region}:

   1. {project_name} ({project_id})
      Pipelines:
      - {pipeline_name} ({pipeline_id}) - {lifecycle_state}
      - {pipeline_name} ({pipeline_id}) - {lifecycle_state}

   2. {project_name} ({project_id})
      Pipelines:
      - {pipeline_name} ({pipeline_id}) - {lifecycle_state}
   ```

### Workflow 4: Check Multiple Recent Deployments

**Use case**: "Show me the last 5 deployments"

1. **Get multiple recent deployments**:
   ```
   get_recent_deployment(project, stage, region, pipeline_id, limit=5)
   ```
   - Returns up to 5 most recent deployments

2. **Present as a table**:
   ```
   Recent deployments for pipeline {pipeline_name}:

   | # | Status    | Started              | Finished             | Duration |
   |---|-----------|----------------------|----------------------|----------|
   | 1 | SUCCEEDED | 2024-01-15 10:30:00 | 2024-01-15 10:35:00 | 5m       |
   | 2 | FAILED    | 2024-01-14 14:00:00 | 2024-01-14 14:02:00 | 2m       |
   | 3 | SUCCEEDED | 2024-01-14 09:00:00 | 2024-01-14 09:08:00 | 8m       |
   ```

## Response Field Reference

### get_recent_deployment Response

| Field | Description |
|-------|-------------|
| `deployment_id` | Unique OCID of the deployment |
| `display_name` | Human-readable deployment name |
| `status` | Lifecycle state (SUCCEEDED, FAILED, IN_PROGRESS, etc.) |
| `is_success` | Boolean - true if SUCCEEDED |
| `is_failed` | Boolean - true if FAILED |
| `is_in_progress` | Boolean - true if still running |
| `time_started` | When deployment execution began |
| `time_finished` | When deployment completed (null if in progress) |
| `lifecycle_details` | Error message if failed |
| `failed_stages` | List of stages that failed |

### get_deployment_logs Response

| Field | Description |
|-------|-------------|
| `deployment_id` | Unique OCID of the deployment |
| `lifecycle_state` | Overall deployment state |
| `lifecycle_details` | Error details/reason for failure |
| `time_created` | When deployment was created |
| `time_started` | When execution started |
| `time_finished` | When execution completed |
| `stages` | List of all stage executions |
| `failed_stages` | List of failed stages with error details |
| `has_failures` | Boolean indicating if any failures occurred |
| `summary` | Human-readable summary of deployment state |

### Deployment Lifecycle States

| State | Description |
|-------|-------------|
| `ACCEPTED` | Deployment request accepted, waiting to start |
| `IN_PROGRESS` | Deployment is currently running |
| `SUCCEEDED` | Deployment completed successfully |
| `FAILED` | Deployment failed |
| `CANCELING` | Deployment is being canceled |
| `CANCELED` | Deployment was canceled |

## Error Handling

- **No deployments found**: Pipeline may be new or all deployments may have been deleted
- **Pipeline not found**: Verify the pipeline_id is correct and in the right compartment
- **Project not found**: Verify the project/stage/region combination in meta.yaml
- **Permission denied**: User may lack IAM permissions to view DevOps resources

## Tips for Troubleshooting Failed Deployments

1. **Check lifecycle_details first** - Contains the primary error message
2. **Review failed_stages** - Identifies which stage(s) caused the failure
3. **Check stage timing** - Long-running stages before failure may indicate timeouts
4. **Look for patterns** - If same stage fails repeatedly, focus investigation there

## Summary Report

After checking deployment status, provide a summary:
- Pipeline name and ID
- Most recent deployment status
- Start and end times
- If failed: failed stage(s) and error details
- If in progress: current stage being executed
- Recommendation for next steps (if applicable)

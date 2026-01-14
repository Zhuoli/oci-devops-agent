# OCI Operations Parallelization Implementation Plan

## Overview

This document outlines the plan to improve performance of OCI DevOps operations by parallelizing API calls that are currently executed sequentially.

**Target Improvement:** 5-10x faster for multi-region, multi-cluster deployments

## Current Performance Bottlenecks

### 1. Multi-Region Processing (Highest Impact)
- **Files:** `ssh_sync.py`, `oke_version_report.py`, `check_image_updates.py`
- **Issue:** Regions processed sequentially, each requiring auth setup + API calls
- **Impact:** 4 regions × 3-5s = 12-20s wait time

### 2. Cluster/Node Pool Queries (High Impact)
- **Files:** `oke_version_report.py`, `oke_node_cycle.py`
- **Issue:** Nested loops - for each cluster, sequentially fetch node pools
- **Impact:** 3 regions × 2 clusters × 3 pools = 18 sequential API calls

### 3. Instance-Level Operations (Medium-High Impact)
- **Files:** `check_image_updates.py`, `node_cycle_pools.py`
- **Issue:** Per-instance API calls for image lookups
- **Impact:** 50 instances × 2-3 calls = 100-150 sequential API calls

## Implementation Phases

### Phase 1: Core Parallel Utilities
Create a shared utility module for parallel execution patterns.

**File:** `tools/src/oci_client/utils/parallel.py`

```python
# Provides:
# - run_parallel_regions() - Execute function across regions in parallel
# - run_parallel_tasks() - Generic parallel task executor with rate limiting
# - Configurable worker counts and error handling
```

### Phase 2: Region-Level Parallelization
Parallelize region processing in main operation files.

**Changes:**
1. `ssh_sync.py` - Parallel region processing for instance collection
2. `oke_version_report.py` - Parallel region processing for cluster/node pool data
3. `check_image_updates.py` - Parallel region processing for image checks

### Phase 3: Cluster/Node Pool Parallelization
Within each region, parallelize cluster and node pool operations.

**Changes:**
1. `oke_version_report.py` - Parallel node pool fetching per cluster
2. `oke_node_cycle.py` - Parallel node pool detail fetching

### Phase 4: Instance-Level Parallelization
Parallelize per-instance operations.

**Changes:**
1. `check_image_updates.py` - Parallel image lookups per instance
2. `oci_client/client.py` - Add parallel-aware methods for batch operations

## Safe Concurrency Limits

Based on OCI API rate limits:

| Operation Level | Max Workers | OCI Rate Limit |
|----------------|-------------|----------------|
| Region | 4 | N/A (different endpoints) |
| Cluster | 6 | Container Engine: 600/min |
| Node Pool | 8 | Container Engine: 600/min |
| Instance | 10 | Compute: 600/min |
| Image Lookup | 6 | Compute: 600/min |

## Error Handling Strategy

1. **Per-region isolation:** One region failure doesn't stop others
2. **Retry with backoff:** Exponential backoff on rate limit (429) errors
3. **Graceful degradation:** Fall back to sequential on persistent failures
4. **Logging:** Log parallel execution stats and any failures

## Implementation Details

### Phase 1: parallel.py Utility Module

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Any, TypeVar
import logging

T = TypeVar('T')
R = TypeVar('R')

def run_parallel_regions(
    region_tasks: Dict[str, Callable[[], T]],
    max_workers: int = 4,
    fail_fast: bool = False
) -> Dict[str, T]:
    """Execute tasks across regions in parallel."""
    pass

def run_parallel_tasks(
    tasks: List[Callable[[], T]],
    max_workers: int = 8
) -> List[T]:
    """Execute a list of tasks in parallel."""
    pass
```

### Phase 2: ssh_sync.py Changes

**Before:**
```python
for region, compartment_id in region_compartments.items():
    oke_instances, odo_instances, bastions = process_region(...)
```

**After:**
```python
from oci_client.utils.parallel import run_parallel_regions

def _process_region_task(project, stage, region, compartment_id):
    return process_region(project, stage, region, compartment_id, ...)

region_tasks = {
    region: lambda r=region, c=comp: _process_region_task(project, stage, r, c)
    for region, comp in region_compartments.items()
}
results = run_parallel_regions(region_tasks, max_workers=4)
```

### Phase 3: oke_version_report.py Changes

**Before:**
```python
for cluster in clusters:
    node_pools = client.list_node_pools(cluster.cluster_id, compartment_id)
```

**After:**
```python
from oci_client.utils.parallel import run_parallel_tasks

def fetch_node_pools(cluster):
    return (cluster, client.list_node_pools(cluster.cluster_id, compartment_id))

tasks = [lambda c=cluster: fetch_node_pools(c) for cluster in clusters]
results = run_parallel_tasks(tasks, max_workers=6)
```

### Phase 4: check_image_updates.py Changes

**Before:**
```python
for inst in instances:
    image = compute_client.get_image(image_id).data
    latest_image = _find_latest_image_with_same_type(...)
```

**After:**
```python
def fetch_instance_images(inst):
    image = compute_client.get_image(inst.source_details.image_id).data
    latest = _find_latest_image_with_same_type(...)
    return (inst, image, latest)

tasks = [lambda i=inst: fetch_instance_images(i) for inst in instances]
results = run_parallel_tasks(tasks, max_workers=10)
```

## Testing Strategy

1. **Unit tests:** Test parallel utility functions with mock tasks
2. **Integration tests:** Test with real OCI API calls (limited scope)
3. **Performance comparison:** Measure before/after times
4. **Rate limit testing:** Verify no 429 errors under normal load

## Rollback Plan

If parallelization causes issues:
1. Set `max_workers=1` to revert to sequential behavior
2. Add `PARALLEL_DISABLED=true` environment variable option
3. Keep original sequential code paths as fallback

## Expected Results

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| SSH Sync (4 regions) | 12-20s | 3-5s | 75% faster |
| OKE Version Report | 5-10s | 1-2s | 80% faster |
| Image Update Check (50 instances) | 20-30s | 3-5s | 85% faster |
| Overall multi-region workflow | 40-60s | 8-12s | 80% faster |

## Files to Modify

1. **New:** `tools/src/oci_client/utils/parallel.py` - Parallel execution utilities
2. **Modify:** `tools/src/ssh_sync.py` - Region-level parallelization
3. **Modify:** `tools/src/oke_version_report.py` - Region + cluster parallelization
4. **Modify:** `tools/src/check_image_updates.py` - Region + instance parallelization
5. **Modify:** `tools/src/oke_node_cycle.py` - Node pool detail parallelization

## Implementation Order

1. Create `parallel.py` utility module
2. Add tests for parallel utilities
3. Update `ssh_sync.py` (simplest, good validation)
4. Update `oke_version_report.py`
5. Update `check_image_updates.py`
6. Update `oke_node_cycle.py`
7. Performance testing and tuning

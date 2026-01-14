"""
Parallel execution utilities for OCI operations.

This module provides utilities for executing OCI API calls in parallel
to improve performance when dealing with multiple regions, clusters,
or instances.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")

# Default worker counts based on OCI rate limits
DEFAULT_REGION_WORKERS = 4
DEFAULT_CLUSTER_WORKERS = 6
DEFAULT_INSTANCE_WORKERS = 10

# Environment variable to disable parallelization (for debugging)
PARALLEL_DISABLED = os.environ.get("OCI_PARALLEL_DISABLED", "").lower() == "true"


@dataclass
class ParallelResult:
    """Result of a parallel task execution."""

    key: str
    success: bool
    result: Optional[Any] = None
    error: Optional[Exception] = None


def run_parallel_regions(
    region_tasks: Dict[str, Callable[[], T]],
    max_workers: int = DEFAULT_REGION_WORKERS,
    fail_fast: bool = False,
) -> Dict[str, ParallelResult]:
    """
    Execute tasks across regions in parallel.

    Args:
        region_tasks: Dictionary mapping region names to callable tasks.
                     Each task should be a no-argument callable that returns the result.
        max_workers: Maximum number of parallel workers (default: 4).
        fail_fast: If True, raise exception on first failure. If False, collect all results.

    Returns:
        Dictionary mapping region names to ParallelResult objects containing
        success status, result, and any error.

    Example:
        region_tasks = {
            "us-phoenix-1": lambda: process_region("us-phoenix-1", compartment_id),
            "us-ashburn-1": lambda: process_region("us-ashburn-1", compartment_id),
        }
        results = run_parallel_regions(region_tasks)
        for region, result in results.items():
            if result.success:
                print(f"{region}: {result.result}")
            else:
                print(f"{region} failed: {result.error}")
    """
    if not region_tasks:
        return {}

    if PARALLEL_DISABLED or max_workers <= 1:
        # Sequential fallback
        logger.debug("Running regions sequentially (parallel disabled or max_workers=1)")
        return _run_sequential(region_tasks)

    results: Dict[str, ParallelResult] = {}
    actual_workers = min(max_workers, len(region_tasks))

    logger.info(f"Processing {len(region_tasks)} regions with {actual_workers} parallel workers")

    with ThreadPoolExecutor(max_workers=actual_workers) as executor:
        # Submit all tasks
        future_to_region = {
            executor.submit(_safe_execute, task): region
            for region, task in region_tasks.items()
        }

        # Collect results as they complete
        for future in as_completed(future_to_region):
            region = future_to_region[future]
            try:
                success, result, error = future.result()
                results[region] = ParallelResult(
                    key=region, success=success, result=result, error=error
                )
                if success:
                    logger.debug(f"Region {region} completed successfully")
                else:
                    logger.warning(f"Region {region} failed: {error}")
                    if fail_fast:
                        raise error  # type: ignore
            except Exception as e:
                results[region] = ParallelResult(key=region, success=False, error=e)
                logger.error(f"Region {region} execution error: {e}")
                if fail_fast:
                    raise

    successful = sum(1 for r in results.values() if r.success)
    logger.info(f"Completed {successful}/{len(region_tasks)} regions successfully")

    return results


def run_parallel_tasks(
    tasks: List[Callable[[], T]],
    max_workers: int = DEFAULT_INSTANCE_WORKERS,
    task_names: Optional[List[str]] = None,
) -> List[ParallelResult]:
    """
    Execute a list of tasks in parallel.

    Args:
        tasks: List of no-argument callables to execute.
        max_workers: Maximum number of parallel workers (default: 10).
        task_names: Optional list of names for logging/debugging.

    Returns:
        List of ParallelResult objects in the same order as input tasks.

    Example:
        tasks = [
            lambda c=cluster: fetch_node_pools(c)
            for cluster in clusters
        ]
        results = run_parallel_tasks(tasks, max_workers=6)
    """
    if PARALLEL_DISABLED or max_workers <= 1:
        # Sequential fallback
        logger.debug("Running tasks sequentially (parallel disabled or max_workers=1)")
        results = []
        for i, task in enumerate(tasks):
            name = task_names[i] if task_names else f"task_{i}"
            success, result, error = _safe_execute(task)
            results.append(ParallelResult(key=name, success=success, result=result, error=error))
        return results

    if not tasks:
        return []

    actual_workers = min(max_workers, len(tasks))
    task_names = task_names or [f"task_{i}" for i in range(len(tasks))]

    logger.debug(f"Processing {len(tasks)} tasks with {actual_workers} parallel workers")

    # We need to maintain order, so we use a dict to track results by index
    results_dict: Dict[int, ParallelResult] = {}

    with ThreadPoolExecutor(max_workers=actual_workers) as executor:
        # Submit all tasks with their index
        future_to_index = {
            executor.submit(_safe_execute, task): i for i, task in enumerate(tasks)
        }

        # Collect results
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            name = task_names[idx]
            try:
                success, result, error = future.result()
                results_dict[idx] = ParallelResult(
                    key=name, success=success, result=result, error=error
                )
            except Exception as e:
                results_dict[idx] = ParallelResult(key=name, success=False, error=e)
                logger.error(f"Task {name} execution error: {e}")

    # Return results in original order
    return [results_dict[i] for i in range(len(tasks))]


def run_parallel_map(
    func: Callable[[T], R],
    items: List[T],
    max_workers: int = DEFAULT_INSTANCE_WORKERS,
    item_name_func: Optional[Callable[[T], str]] = None,
) -> List[Tuple[T, Optional[R], Optional[Exception]]]:
    """
    Apply a function to a list of items in parallel (like parallel map).

    Args:
        func: Function to apply to each item.
        items: List of items to process.
        max_workers: Maximum number of parallel workers.
        item_name_func: Optional function to get a name for each item (for logging).

    Returns:
        List of tuples (item, result, error) in the same order as input items.
        If successful, error is None. If failed, result is None.

    Example:
        def fetch_image(instance):
            return compute_client.get_image(instance.image_id).data

        results = run_parallel_map(fetch_image, instances, max_workers=10)
        for instance, image, error in results:
            if error is None:
                print(f"{instance.id}: {image.display_name}")
    """
    if PARALLEL_DISABLED or max_workers <= 1 or not items:
        # Sequential fallback
        results = []
        for item in items:
            try:
                result = func(item)
                results.append((item, result, None))
            except Exception as e:
                results.append((item, None, e))
        return results

    actual_workers = min(max_workers, len(items))
    logger.debug(f"Processing {len(items)} items with {actual_workers} parallel workers")

    results_dict: Dict[int, Tuple[T, Optional[R], Optional[Exception]]] = {}

    with ThreadPoolExecutor(max_workers=actual_workers) as executor:
        future_to_index = {
            executor.submit(func, item): i for i, item in enumerate(items)
        }

        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            item = items[idx]
            try:
                result = future.result()
                results_dict[idx] = (item, result, None)
            except Exception as e:
                item_name = item_name_func(item) if item_name_func else str(idx)
                logger.warning(f"Failed to process item {item_name}: {e}")
                results_dict[idx] = (item, None, e)

    return [results_dict[i] for i in range(len(items))]


def _safe_execute(task: Callable[[], T]) -> Tuple[bool, Optional[T], Optional[Exception]]:
    """
    Safely execute a task and catch any exceptions.

    Returns:
        Tuple of (success, result, error)
    """
    try:
        result = task()
        return (True, result, None)
    except Exception as e:
        return (False, None, e)


def _run_sequential(
    region_tasks: Dict[str, Callable[[], T]]
) -> Dict[str, ParallelResult]:
    """Run region tasks sequentially (fallback mode)."""
    results: Dict[str, ParallelResult] = {}
    for region, task in region_tasks.items():
        success, result, error = _safe_execute(task)
        results[region] = ParallelResult(
            key=region, success=success, result=result, error=error
        )
        if success:
            logger.debug(f"Region {region} completed successfully")
        else:
            logger.warning(f"Region {region} failed: {error}")
    return results


def get_worker_count(
    level: str, item_count: int, override: Optional[int] = None
) -> int:
    """
    Get the appropriate worker count for a parallelization level.

    Args:
        level: One of "region", "cluster", "instance"
        item_count: Number of items to process
        override: Optional override value

    Returns:
        Number of workers to use
    """
    if override is not None:
        return min(override, item_count)

    defaults = {
        "region": DEFAULT_REGION_WORKERS,
        "cluster": DEFAULT_CLUSTER_WORKERS,
        "instance": DEFAULT_INSTANCE_WORKERS,
    }

    max_workers = defaults.get(level, DEFAULT_INSTANCE_WORKERS)
    return min(max_workers, item_count)

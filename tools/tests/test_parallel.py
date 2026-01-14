"""Tests for parallel execution utilities."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from src.oci_client.utils.parallel import (
    DEFAULT_CLUSTER_WORKERS,
    DEFAULT_INSTANCE_WORKERS,
    DEFAULT_REGION_WORKERS,
    ParallelResult,
    get_worker_count,
    run_parallel_map,
    run_parallel_regions,
    run_parallel_tasks,
)


class TestParallelResult:
    """Test ParallelResult dataclass."""

    def test_parallel_result_creation(self):
        """Test creating a ParallelResult."""
        result = ParallelResult(
            key="test_region",
            success=True,
            result={"data": "value"},
            error=None,
        )
        assert result.key == "test_region"
        assert result.success is True
        assert result.result == {"data": "value"}
        assert result.error is None

    def test_parallel_result_with_error(self):
        """Test creating a ParallelResult with an error."""
        error = ValueError("Something went wrong")
        result = ParallelResult(
            key="failed_task",
            success=False,
            result=None,
            error=error,
        )
        assert result.success is False
        assert result.error is error


class TestRunParallelRegions:
    """Test run_parallel_regions function."""

    def test_basic_parallel_execution(self):
        """Test basic parallel region execution."""
        results_order = []

        def task_a():
            results_order.append("a")
            return "result_a"

        def task_b():
            results_order.append("b")
            return "result_b"

        region_tasks = {
            "region-a": task_a,
            "region-b": task_b,
        }

        results = run_parallel_regions(region_tasks, max_workers=2)

        assert len(results) == 2
        assert results["region-a"].success is True
        assert results["region-a"].result == "result_a"
        assert results["region-b"].success is True
        assert results["region-b"].result == "result_b"

    def test_handles_task_exception(self):
        """Test that exceptions in tasks are captured."""

        def failing_task():
            raise ValueError("Task failed")

        def successful_task():
            return "success"

        region_tasks = {
            "failing": failing_task,
            "success": successful_task,
        }

        results = run_parallel_regions(region_tasks, max_workers=2)

        assert results["failing"].success is False
        assert isinstance(results["failing"].error, ValueError)
        assert results["success"].success is True
        assert results["success"].result == "success"

    def test_empty_tasks(self):
        """Test with empty task dictionary."""
        results = run_parallel_regions({}, max_workers=2)
        assert results == {}

    def test_single_worker_sequential(self):
        """Test that max_workers=1 runs sequentially."""
        execution_order = []

        def task_1():
            execution_order.append(1)
            return 1

        def task_2():
            execution_order.append(2)
            return 2

        region_tasks = {
            "r1": task_1,
            "r2": task_2,
        }

        results = run_parallel_regions(region_tasks, max_workers=1)

        # With sequential execution, both should succeed
        assert results["r1"].success is True
        assert results["r2"].success is True
        # Order should be deterministic with max_workers=1
        assert len(execution_order) == 2

    @patch.dict(os.environ, {"OCI_PARALLEL_DISABLED": "true"})
    def test_parallel_disabled_env_var(self):
        """Test that PARALLEL_DISABLED environment variable forces sequential execution."""
        # Need to reload module to pick up env var
        from importlib import reload

        from src.oci_client.utils import parallel

        reload(parallel)

        assert parallel.PARALLEL_DISABLED is True

        # Cleanup
        os.environ.pop("OCI_PARALLEL_DISABLED", None)
        reload(parallel)


class TestRunParallelTasks:
    """Test run_parallel_tasks function."""

    def test_basic_task_execution(self):
        """Test basic parallel task execution."""
        tasks = [
            lambda: "result_0",
            lambda: "result_1",
            lambda: "result_2",
        ]

        results = run_parallel_tasks(tasks, max_workers=3)

        assert len(results) == 3
        # Results should be in order
        for i, result in enumerate(results):
            assert result.success is True
            assert result.result == f"result_{i}"

    def test_preserves_order(self):
        """Test that results maintain input order."""
        import time

        def slow_task():
            time.sleep(0.05)
            return "slow"

        def fast_task():
            return "fast"

        tasks = [slow_task, fast_task, fast_task, slow_task]
        results = run_parallel_tasks(tasks, max_workers=4)

        # Even with different completion times, order is preserved
        assert len(results) == 4
        assert results[0].result == "slow"
        assert results[1].result == "fast"
        assert results[2].result == "fast"
        assert results[3].result == "slow"

    def test_handles_exceptions(self):
        """Test that exceptions are captured per task."""

        def success():
            return "ok"

        def failure():
            raise RuntimeError("boom")

        tasks = [success, failure, success]
        results = run_parallel_tasks(tasks, max_workers=3)

        assert results[0].success is True
        assert results[0].result == "ok"
        assert results[1].success is False
        assert isinstance(results[1].error, RuntimeError)
        assert results[2].success is True

    def test_empty_task_list(self):
        """Test with empty task list."""
        results = run_parallel_tasks([], max_workers=5)
        assert results == []

    def test_with_task_names(self):
        """Test task execution with custom names."""
        tasks = [lambda: "a", lambda: "b"]
        task_names = ["task_a", "task_b"]

        results = run_parallel_tasks(tasks, max_workers=2, task_names=task_names)

        assert results[0].key == "task_a"
        assert results[1].key == "task_b"


class TestRunParallelMap:
    """Test run_parallel_map function."""

    def test_basic_map(self):
        """Test basic parallel map operation."""

        def double(x):
            return x * 2

        items = [1, 2, 3, 4, 5]
        results = run_parallel_map(double, items, max_workers=3)

        assert len(results) == 5
        for i, (item, result, error) in enumerate(results):
            assert item == items[i]
            assert result == items[i] * 2
            assert error is None

    def test_preserves_order(self):
        """Test that map results maintain input order."""

        def identity(x):
            return x

        items = ["a", "b", "c", "d"]
        results = run_parallel_map(identity, items, max_workers=4)

        for i, (item, result, error) in enumerate(results):
            assert item == items[i]
            assert result == items[i]

    def test_handles_exceptions(self):
        """Test that exceptions are captured per item."""

        def process(x):
            if x == 2:
                raise ValueError(f"Cannot process {x}")
            return x * 10

        items = [1, 2, 3]
        results = run_parallel_map(process, items, max_workers=3)

        assert results[0] == (1, 10, None)
        assert results[1][0] == 2
        assert results[1][1] is None
        assert isinstance(results[1][2], ValueError)
        assert results[2] == (3, 30, None)

    def test_empty_items(self):
        """Test with empty item list."""
        results = run_parallel_map(lambda x: x, [], max_workers=5)
        assert results == []

    def test_with_item_name_func(self):
        """Test with custom item name function for logging."""
        items = [{"id": 1}, {"id": 2}]

        def process(item):
            return item["id"] * 2

        def get_name(item):
            return f"item_{item['id']}"

        # This should not raise even if logging is triggered
        results = run_parallel_map(
            process, items, max_workers=2, item_name_func=get_name
        )

        assert len(results) == 2


class TestGetWorkerCount:
    """Test get_worker_count function."""

    def test_default_region_workers(self):
        """Test default region worker count."""
        count = get_worker_count("region", 10)
        assert count == DEFAULT_REGION_WORKERS

    def test_default_cluster_workers(self):
        """Test default cluster worker count."""
        count = get_worker_count("cluster", 10)
        assert count == DEFAULT_CLUSTER_WORKERS

    def test_default_instance_workers(self):
        """Test default instance worker count."""
        count = get_worker_count("instance", 20)
        assert count == DEFAULT_INSTANCE_WORKERS

    def test_limited_by_item_count(self):
        """Test that worker count is limited by item count."""
        # Only 2 items, even though default is 4
        count = get_worker_count("region", 2)
        assert count == 2

    def test_override_value(self):
        """Test override parameter."""
        count = get_worker_count("region", 10, override=2)
        assert count == 2

    def test_override_limited_by_items(self):
        """Test that override is still limited by item count."""
        count = get_worker_count("region", 3, override=10)
        assert count == 3

    def test_unknown_level_uses_instance_default(self):
        """Test that unknown level falls back to instance workers."""
        count = get_worker_count("unknown", 20)
        assert count == DEFAULT_INSTANCE_WORKERS


class TestParallelPerformance:
    """Test that parallelization actually improves performance."""

    def test_parallel_faster_than_sequential(self):
        """Test that parallel execution is faster than sequential for IO-bound tasks."""

        def slow_task():
            time.sleep(0.05)
            return "done"

        tasks = [slow_task for _ in range(4)]

        # Parallel execution
        start_parallel = time.time()
        run_parallel_tasks(tasks, max_workers=4)
        parallel_time = time.time() - start_parallel

        # Sequential execution
        start_sequential = time.time()
        run_parallel_tasks(tasks, max_workers=1)
        sequential_time = time.time() - start_sequential

        # Parallel should be significantly faster (at least 2x)
        # 4 tasks * 0.05s = 0.2s sequential vs ~0.05s parallel
        assert parallel_time < sequential_time * 0.6

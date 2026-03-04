"""Tests for rustlette.background — BackgroundTask, BackgroundTasks."""

import pytest

from rustlette.background import BackgroundTask, BackgroundTasks


class TestBackgroundTask:
    @pytest.mark.anyio
    async def test_sync_task(self):
        results = []

        def task(value):
            results.append(value)

        bt = BackgroundTask(task, "hello")
        await bt()
        assert results == ["hello"]

    @pytest.mark.anyio
    async def test_async_task(self):
        results = []

        async def task(value):
            results.append(value)

        bt = BackgroundTask(task, "async_hello")
        await bt()
        assert results == ["async_hello"]

    @pytest.mark.anyio
    async def test_task_with_kwargs(self):
        results = {}

        def task(key, value="default"):
            results[key] = value

        bt = BackgroundTask(task, "k", value="v")
        await bt()
        assert results == {"k": "v"}


class TestBackgroundTasks:
    @pytest.mark.anyio
    async def test_multiple_tasks(self):
        results = []

        def task1():
            results.append("task1")

        async def task2():
            results.append("task2")

        tasks = BackgroundTasks()
        tasks.add_task(task1)
        tasks.add_task(task2)
        await tasks()
        assert results == ["task1", "task2"]

    @pytest.mark.anyio
    async def test_tasks_with_args(self):
        results = []

        def task(value):
            results.append(value)

        tasks = BackgroundTasks()
        tasks.add_task(task, "a")
        tasks.add_task(task, "b")
        await tasks()
        assert results == ["a", "b"]

    @pytest.mark.anyio
    async def test_empty_tasks(self):
        tasks = BackgroundTasks()
        await tasks()  # Should not raise

    @pytest.mark.anyio
    async def test_initial_tasks(self):
        results = []

        def task():
            results.append("init")

        tasks = BackgroundTasks(tasks=[BackgroundTask(task)])
        await tasks()
        assert results == ["init"]

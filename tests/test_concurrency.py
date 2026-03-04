"""Tests for rustlette.concurrency — run_in_threadpool, iterate_in_threadpool."""

import pytest

from rustlette.concurrency import iterate_in_threadpool, run_in_threadpool


class TestRunInThreadpool:
    @pytest.mark.anyio
    async def test_sync_function(self):
        def sync_add(a, b):
            return a + b

        result = await run_in_threadpool(sync_add, 3, 4)
        assert result == 7

    @pytest.mark.anyio
    async def test_sync_function_kwargs(self):
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = await run_in_threadpool(greet, "World", greeting="Hi")
        assert result == "Hi, World!"

    @pytest.mark.anyio
    async def test_async_function_passed_through(self):
        """Starlette's run_in_threadpool does NOT special-case async functions.
        It runs them in the threadpool like any callable, returning a coroutine object."""

        async def async_add(a, b):
            return a + b

        result = await run_in_threadpool(async_add, 3, 4)
        # Result is a coroutine (not awaited), matching Starlette behavior
        import inspect

        assert inspect.iscoroutine(result)
        result.close()  # cleanup to avoid RuntimeWarning

    @pytest.mark.anyio
    async def test_exception_propagation(self):
        def fail():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await run_in_threadpool(fail)


class TestIterateInThreadpool:
    @pytest.mark.anyio
    async def test_basic_iteration(self):
        def sync_gen():
            yield 1
            yield 2
            yield 3

        result = []
        async for item in iterate_in_threadpool(sync_gen()):
            result.append(item)
        assert result == [1, 2, 3]

    @pytest.mark.anyio
    async def test_empty_iterator(self):
        result = []
        async for item in iterate_in_threadpool(iter([])):
            result.append(item)
        assert result == []

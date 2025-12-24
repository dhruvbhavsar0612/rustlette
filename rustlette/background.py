"""
Background task management for Rustlette
"""

import asyncio
import typing
from typing import Any, Callable, Dict, List, Optional, Union

from ._rustlette_core import BackgroundTask as _BackgroundTask


class BackgroundTasks:
    """
    Container for background tasks to be executed after response is sent.
    """

    def __init__(self, tasks: Optional[List[_BackgroundTask]] = None) -> None:
        """
        Initialize background tasks container.

        Args:
            tasks: Optional list of initial tasks
        """
        self._tasks: List[_BackgroundTask] = list(tasks or [])

    def add_task(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Add a background task.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        task = _BackgroundTask(
            func=func,
            args=list(args),
            kwargs=kwargs if kwargs else None,
        )
        self._tasks.append(task)

    def add_task_with_delay(
        self,
        func: Callable[..., Any],
        delay: float,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Add a background task with delay.

        Args:
            func: Function to execute
            delay: Delay in seconds before execution
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        task = _BackgroundTask(
            func=func,
            args=list(args),
            kwargs=kwargs if kwargs else None,
            delay=delay,
        )
        self._tasks.append(task)

    def add_task_with_retry(
        self,
        func: Callable[..., Any],
        max_retries: int = 3,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Add a background task with retry logic.

        Args:
            func: Function to execute
            max_retries: Maximum number of retry attempts
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        task = _BackgroundTask(
            func=func,
            args=list(args),
            kwargs=kwargs if kwargs else None,
            max_retries=max_retries,
        )
        self._tasks.append(task)

    async def __call__(self) -> None:
        """Execute all background tasks."""
        for task in self._tasks:
            try:
                task.execute()
            except Exception as e:
                # Log the error but don't let it affect other tasks
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Background task failed: {e}")

    def __len__(self) -> int:
        """Return number of tasks."""
        return len(self._tasks)

    def __bool__(self) -> bool:
        """Return True if there are tasks."""
        return bool(self._tasks)

    def __iter__(self) -> typing.Iterator[_BackgroundTask]:
        """Iterate over tasks."""
        return iter(self._tasks)

    def clear(self) -> None:
        """Clear all tasks."""
        self._tasks.clear()

    def extend(self, other: "BackgroundTasks") -> None:
        """Extend with tasks from another container."""
        self._tasks.extend(other._tasks)

    def __repr__(self) -> str:
        return f"BackgroundTasks({len(self._tasks)} tasks)"


# Common background task helpers
def send_email_task(
    to: str,
    subject: str,
    body: str,
    smtp_config: Optional[Dict[str, Any]] = None,
) -> Callable[[], None]:
    """
    Create a background task for sending email.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        smtp_config: SMTP configuration

    Returns:
        Function that can be added as background task
    """

    def task():
        # This would integrate with an email library
        # For now, just log the action
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Sending email to {to}: {subject}")

    return task


def cleanup_temp_files_task(*file_paths: str) -> Callable[[], None]:
    """
    Create a background task for cleaning up temporary files.

    Args:
        *file_paths: Paths of files to delete

    Returns:
        Function that can be added as background task
    """

    def task():
        import os

        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass  # Ignore errors when cleaning up

    return task


def log_event_task(
    event: str,
    level: str = "info",
    extra_data: Optional[Dict[str, Any]] = None,
) -> Callable[[], None]:
    """
    Create a background task for logging events.

    Args:
        event: Event message
        level: Log level (debug, info, warning, error, critical)
        extra_data: Additional data to log

    Returns:
        Function that can be added as background task
    """

    def task():
        import logging

        logger = logging.getLogger(__name__)

        log_func = getattr(logger, level.lower(), logger.info)
        if extra_data:
            log_func(f"{event} - {extra_data}")
        else:
            log_func(event)

    return task


def webhook_task(
    url: str,
    data: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Callable[[], None]:
    """
    Create a background task for sending webhooks.

    Args:
        url: Webhook URL
        data: Data to send
        headers: HTTP headers
        timeout: Request timeout

    Returns:
        Function that can be added as background task
    """

    def task():
        # This would use an HTTP client like httpx
        # For now, just log the action
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Sending webhook to {url} with data: {data}")

    return task


def database_cleanup_task(
    table: str,
    condition: str,
    db_config: Optional[Dict[str, Any]] = None,
) -> Callable[[], None]:
    """
    Create a background task for database cleanup.

    Args:
        table: Table name
        condition: WHERE condition
        db_config: Database configuration

    Returns:
        Function that can be added as background task
    """

    def task():
        # This would integrate with a database library
        # For now, just log the action
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Cleaning up {table} where {condition}")

    return task


def cache_warm_up_task(
    cache_keys: List[str],
    cache_config: Optional[Dict[str, Any]] = None,
) -> Callable[[], None]:
    """
    Create a background task for cache warm-up.

    Args:
        cache_keys: Keys to warm up
        cache_config: Cache configuration

    Returns:
        Function that can be added as background task
    """

    def task():
        # This would integrate with a cache library like Redis
        # For now, just log the action
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Warming up cache keys: {cache_keys}")

    return task


# Async background task helpers
async def async_send_email_task(
    to: str,
    subject: str,
    body: str,
    smtp_config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Async version of send_email_task.
    """
    # This would use an async email library
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Async sending email to {to}: {subject}")


async def async_webhook_task(
    url: str,
    data: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> None:
    """
    Async version of webhook_task.
    """
    # This would use httpx or similar async HTTP client
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Async sending webhook to {url} with data: {data}")


async def async_database_operation_task(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    db_config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Async database operation task.
    """
    # This would use an async database library like asyncpg
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Async executing query: {query} with params: {params}")


# Task scheduling helpers
class TaskScheduler:
    """
    Simple task scheduler for background tasks.
    """

    def __init__(self) -> None:
        self._scheduled_tasks: List[Dict[str, Any]] = []

    def schedule_task(
        self,
        func: Callable[..., Any],
        delay: float,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Schedule a task to run after a delay.

        Args:
            func: Function to execute
            delay: Delay in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        import time

        scheduled_time = time.time() + delay
        self._scheduled_tasks.append(
            {
                "func": func,
                "args": args,
                "kwargs": kwargs,
                "scheduled_time": scheduled_time,
            }
        )

    def schedule_recurring_task(
        self,
        func: Callable[..., Any],
        interval: float,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Schedule a recurring task.

        Args:
            func: Function to execute
            interval: Interval in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        # This would need a proper scheduler implementation
        # For now, just schedule once
        self.schedule_task(func, interval, *args, **kwargs)

    async def run_scheduled_tasks(self) -> None:
        """
        Run all scheduled tasks that are due.
        """
        import time

        current_time = time.time()
        due_tasks = [
            task
            for task in self._scheduled_tasks
            if task["scheduled_time"] <= current_time
        ]

        for task in due_tasks:
            try:
                if asyncio.iscoroutinefunction(task["func"]):
                    await task["func"](*task["args"], **task["kwargs"])
                else:
                    task["func"](*task["args"], **task["kwargs"])
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Scheduled task failed: {e}")

        # Remove completed tasks
        self._scheduled_tasks = [
            task
            for task in self._scheduled_tasks
            if task["scheduled_time"] > current_time
        ]

    def clear_scheduled_tasks(self) -> None:
        """Clear all scheduled tasks."""
        self._scheduled_tasks.clear()

    def __len__(self) -> int:
        """Return number of scheduled tasks."""
        return len(self._scheduled_tasks)


# Global task scheduler instance
_global_scheduler = TaskScheduler()


def schedule_task(
    func: Callable[..., Any],
    delay: float,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Schedule a task globally.
    """
    _global_scheduler.schedule_task(func, delay, *args, **kwargs)


def schedule_recurring_task(
    func: Callable[..., Any],
    interval: float,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Schedule a recurring task globally.
    """
    _global_scheduler.schedule_recurring_task(func, interval, *args, **kwargs)


async def run_scheduled_tasks() -> None:
    """
    Run all globally scheduled tasks.
    """
    await _global_scheduler.run_scheduled_tasks()

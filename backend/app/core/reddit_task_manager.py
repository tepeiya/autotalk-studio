"""Reddit Task Manager - Reddit 业务线任务调度 + SSE 事件流。

独立于 video task_manager，不互相影响。
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from typing import AsyncIterator

from ..core.schemas import RedditTask, RedditTaskCreate, RedditTaskEvent, RedditTaskStatus
from ..core.reddit_pipeline import RedditPipeline

logger = logging.getLogger(__name__)


class RedditTaskManager:
    """Reddit 业务线任务管理器（单例）。"""

    def __init__(self, max_workers: int = 2) -> None:
        self.max_workers = max_workers
        self._tasks: dict[str, RedditTask] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._events: dict[str, list[RedditTaskEvent]] = defaultdict(list)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._running_pipelines: dict[str, RedditPipeline] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())

    def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None

    def submit(self, params: RedditTaskCreate) -> RedditTask:
        task_id = f"rtask_{uuid.uuid4().hex[:12]}"
        task = RedditTask(id=task_id, params=params)
        self._tasks[task_id] = task
        self._queue.put_nowait(task_id)
        self.start()
        return task

    def cancel(self, task_id: str) -> bool:
        if task_id in self._running_pipelines:
            self._running_pipelines[task_id].cancel()
            return True
        return False

    def get(self, task_id: str) -> RedditTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, status: RedditTaskStatus | None = None) -> list[RedditTask]:
        items = list(self._tasks.values())
        if status:
            items = [t for t in items if t.status == status]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def events(self, task_id: str) -> list[RedditTaskEvent]:
        return list(self._events[task_id])

    async def subscribe(self, task_id: str) -> AsyncIterator[RedditTaskEvent]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[task_id].append(q)
        for ev in self._events[task_id]:
            await q.put(ev)
        try:
            while True:
                ev = await q.get()
                yield ev
                if ev.status in (RedditTaskStatus.SUCCESS, RedditTaskStatus.FAILED,
                                  RedditTaskStatus.CANCELLED) \
                        and ev.stage in ("done", "error"):
                    break
        finally:
            self._subscribers[task_id].remove(q)

    def _publish(self, event: RedditTaskEvent) -> None:
        self._events[event.task_id].append(event)
        for q in self._subscribers[event.task_id]:
            q.put_nowait(event)

    async def _worker_loop(self) -> None:
        sem = asyncio.Semaphore(self.max_workers)
        while True:
            task_id = await self._queue.get()
            asyncio.create_task(self._run_with_sem(sem, task_id))

    async def _run_with_sem(self, sem: asyncio.Semaphore, task_id: str) -> None:
        async with sem:
            await self._run_task(task_id)

    async def _run_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return

        def on_event(ev: RedditTaskEvent) -> None:
            self._publish(ev)

        pipeline = RedditPipeline(task, on_event=on_event)
        self._running_pipelines[task_id] = pipeline
        coro_task = asyncio.create_task(pipeline.run())
        self._running_tasks[task_id] = coro_task
        try:
            await coro_task
        except asyncio.CancelledError:
            task.status = RedditTaskStatus.CANCELLED
            self._publish(RedditTaskEvent(
                task_id=task_id,
                stage="cancelled",
                status=RedditTaskStatus.CANCELLED,
                message="用户取消",
            ))
        except Exception as e:
            logger.exception("Reddit task failed: %s", task_id)
            task.status = RedditTaskStatus.FAILED
            task.error = str(e)
        finally:
            self._running_pipelines.pop(task_id, None)
            self._running_tasks.pop(task_id, None)


# 全局单例
reddit_task_manager = RedditTaskManager(max_workers=2)

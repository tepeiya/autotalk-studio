"""Task Manager - 批量任务调度 + 内存存储 + SSE 事件广播。

借鉴 LuoGen-agent 的批量任务调度 + MoneyPrinterTurbo 的批量生成。
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from typing import AsyncIterator

from ..core.schemas import Project, TaskEvent, TaskStatus
from ..core.pipeline import Pipeline

logger = logging.getLogger(__name__)


class TaskManager:
    """内存级任务管理器（后续可换 Redis 持久化）。"""

    def __init__(self, max_workers: int = 2) -> None:
        self.max_workers = max_workers
        self._projects: dict[str, Project] = {}
        self._queue: asyncio.Queue[str] = deque() if False else asyncio.Queue()
        self._events: dict[str, list[TaskEvent]] = defaultdict(list)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())

    def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None

    # ────────── 项目管理 ──────────

    def submit(self, project: Project) -> Project:
        self._projects[project.id] = project
        self._queue.put_nowait(project.id)
        self.start()
        return project

    def cancel(self, project_id: str) -> bool:
        if project_id in self._running_tasks:
            self._running_tasks[project_id].cancel()
            return True
        return False

    def get(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def list_projects(self, status: TaskStatus | None = None) -> list[Project]:
        items = list(self._projects.values())
        if status:
            items = [p for p in items if p.status == status]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    # ────────── 事件订阅 ──────────

    def events(self, project_id: str) -> list[TaskEvent]:
        return list(self._events[project_id])

    async def subscribe(self, project_id: str) -> AsyncIterator[TaskEvent]:
        """订阅某项目的实时事件流（SSE 用）。"""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[project_id].append(q)
        # 先把已积累的事件发出
        for ev in self._events[project_id]:
            await q.put(ev)
        try:
            while True:
                ev = await q.get()
                yield ev
                if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED) \
                        and ev.stage in ("done", "error"):
                    break
        finally:
            self._subscribers[project_id].remove(q)

    def _publish(self, event: TaskEvent) -> None:
        self._events[event.project_id].append(event)
        for q in self._subscribers[event.project_id]:
            q.put_nowait(event)

    # ────────── Worker ──────────

    async def _worker_loop(self) -> None:
        """简单 worker：限制并发数。"""
        sem = asyncio.Semaphore(self.max_workers)
        while True:
            project_id = await self._queue.get()
            asyncio.create_task(self._run_with_sem(sem, project_id))

    async def _run_with_sem(self, sem: asyncio.Semaphore, project_id: str) -> None:
        async with sem:
            await self._run_project(project_id)

    async def _run_project(self, project_id: str) -> None:
        project = self._projects.get(project_id)
        if not project:
            return

        def on_event(ev: TaskEvent) -> None:
            self._publish(ev)

        pipeline = Pipeline(project, on_event=on_event)
        task = asyncio.create_task(pipeline.run())
        self._running_tasks[project_id] = task
        try:
            await task
        except asyncio.CancelledError:
            project.status = TaskStatus.CANCELLED
            self._publish(TaskEvent(
                project_id=project_id,
                stage="cancelled",
                status=TaskStatus.CANCELLED,
                message="用户取消",
            ))
        except Exception as e:
            logger.exception("Task failed: %s", project_id)
            project.status = TaskStatus.FAILED
            project.error = str(e)
        finally:
            self._running_tasks.pop(project_id, None)


# 全局单例
task_manager = TaskManager(max_workers=2)

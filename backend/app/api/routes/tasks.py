"""Tasks API - SSE 实时进度流 + 历史事件。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ...core.schemas import TaskEvent
from ...core.task_manager import task_manager

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{project_id}/events", response_model=list[TaskEvent])
async def list_events(project_id: str) -> list[TaskEvent]:
    return task_manager.events(project_id)


@router.get("/{project_id}/stream")
async def stream_events(project_id: str):
    """SSE 端点：实时推送任务进度。"""
    if not task_manager.get(project_id):
        raise HTTPException(404, "Project not found")

    async def event_gen():
        async for ev in task_manager.subscribe(project_id):
            yield {
                "event": ev.stage,
                "data": ev.model_dump_json(),
            }

    return EventSourceResponse(event_gen())

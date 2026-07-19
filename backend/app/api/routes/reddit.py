"""Reddit API - Reddit 业务线路由。"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ...core.reddit_task_manager import reddit_task_manager
from ...core.schemas import RedditTaskCreate, RedditTaskStatus
from ...core.storage import get_storage
from ...providers.base import registry as preg

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reddit", tags=["reddit"])


@router.get("/providers")
async def list_reddit_providers():
    """列出 Reddit 业务线相关 provider。"""
    result = {}
    for ptype in ("collector", "translator", "image", "note"):
        items = preg.list_providers(type_filter=ptype)
        result[ptype] = [
            {
                "name": it["name"],
                "requires_gpu": it.get("requires_gpu", False),
                "class": it.get("class", it["name"]),
            }
            for it in items
        ]
    return result


@router.post("/collect")
async def collect_only(params: RedditTaskCreate):
    """仅触发采集（不启动完整 pipeline），返回原始热帖列表。"""
    collector = preg.create("collector", params.collector)
    posts = await collector.collect(
        source=params.subreddit,
        limit=params.limit,
        time_filter=params.time_filter,
    )
    return {"subreddit": params.subreddit, "count": len(posts), "posts": posts}


@router.post("/tasks")
async def create_task(params: RedditTaskCreate):
    """创建并自动提交 Reddit 任务。"""
    task = reddit_task_manager.submit(params)
    return task.model_dump()


@router.get("/tasks")
async def list_tasks(
    status: RedditTaskStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    items = reddit_task_manager.list_tasks(status=status)[:limit]
    return [t.model_dump() for t in items]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    t = reddit_task_manager.get(task_id)
    if not t:
        raise HTTPException(404, f"Reddit task not found: {task_id}")
    return t.model_dump()


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    if not reddit_task_manager.cancel(task_id):
        raise HTTPException(404, "Task not running")
    return {"ok": True, "task_id": task_id}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    if task_id in reddit_task_manager._tasks:
        reddit_task_manager._tasks.pop(task_id)
        reddit_task_manager._events.pop(task_id, None)
        return {"ok": True}
    raise HTTPException(404, "Task not found")


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    """SSE 实时事件流。"""
    if not reddit_task_manager.get(task_id):
        raise HTTPException(404, f"Task not found: {task_id}")

    async def event_gen():
        async for ev in reddit_task_manager.subscribe(task_id):
            yield {
                "event": ev.stage,
                "data": ev.model_dump_json(),
            }

    return EventSourceResponse(event_gen())


@router.get("/tasks/{task_id}/events")
async def list_events(task_id: str):
    """已积累的事件列表（非流式）。"""
    if not reddit_task_manager.get(task_id):
        raise HTTPException(404, "Task not found")
    return [ev.model_dump() for ev in reddit_task_manager.events(task_id)]


@router.get("/notes/{task_id}/{post_id}")
async def get_note_content(task_id: str, post_id: str):
    """读取笔记 markdown 原文。"""
    storage = get_storage()
    note_path = storage.reddit_notes_dir / task_id / f"{post_id}.md"
    if not note_path.exists():
        raise HTTPException(404, "Note not found")
    return {
        "task_id": task_id,
        "post_id": post_id,
        "path": str(note_path),
        "url": f"/static/reddit/notes/{task_id}/{post_id}.md",
        "content": note_path.read_text(encoding="utf-8"),
    }

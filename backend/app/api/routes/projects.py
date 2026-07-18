"""Projects API - 创建/查询/取消项目。"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException

from ...core.schemas import Project, ProjectCreate, TaskStatus
from ...core.storage import get_storage
from ...core.task_manager import task_manager

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=Project)
async def create_project(req: ProjectCreate) -> Project:
    project = Project(
        id=f"proj_{uuid.uuid4().hex[:12]}",
        **req.model_dump(),
    )
    task_manager.submit(project)
    return project


@router.get("", response_model=list[Project])
async def list_projects(status: TaskStatus | None = None):
    return task_manager.list_projects(status=status)


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    p = task_manager.get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.post("/{project_id}/cancel")
async def cancel_project(project_id: str):
    ok = task_manager.cancel(project_id)
    return {"cancelled": ok}


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    p = task_manager.get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    # 简化：从内存删除（生产可加软删除标记）
    task_manager._projects.pop(project_id, None)
    return {"deleted": project_id}

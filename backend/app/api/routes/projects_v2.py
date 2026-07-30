"""Projects API v2 - 预检 / 费用估算 / 预览审批流。

关键原则：
1. 所有接口都是"新增"，不修改原有 POST /projects 的行为 —— 保证旧代码 100% 兼容
2. 预检与费用估算**不产生副作用**（不扣 API 额度、不写文件、不调外部网络）
3. 新流程：
   POST /projects/preflight → 返回预检报告
   POST /projects/cost      → 返回费用估算
   POST /projects           → 原有（或加了 preview_mode 的创建参数，默认全量）
   POST /projects/{id}/preview   → 只对未开始的项目，触发 15s 预览
   POST /projects/{id}/approve   → 预览 OK → 批准，开始全量合成；不 OK → 驳回
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from ...core.cost_estimator import estimate_cost
from ...core.preflight import run_preflight
from ...core.schemas import (
    CostEstimateResult,
    PreflightResult,
    Project,
    ProjectApproveRequest,
    ProjectCreate,
    TaskEvent,
    TaskStatus,
)
from ...core.task_manager import task_manager

router = APIRouter(prefix="/projects", tags=["projects-v2"])


# ───────────────── 1) 预检 ─────────────────


@router.post("/preflight", response_model=PreflightResult)
async def projects_preflight(req: ProjectCreate) -> PreflightResult:
    """对项目参数做资产预检（不扣额度、不写文件）。"""
    return run_preflight(req)


# ───────────────── 2) 费用估算 ─────────────────


@router.post("/cost", response_model=CostEstimateResult)
async def projects_cost(req: ProjectCreate) -> CostEstimateResult:
    """估算单项目费用（基于静态单价表，实际以服务商账单为准）。"""
    return estimate_cost(req)


# ───────────────── 3) 创建项目（保留与原 POST /projects 等价的行为，多了预览模式开关）─────────
# 注：原 /projects 已经在 routes/projects.py。这里新增 /projects_v2 等价路由 + 预检前置开关，
# 方便前端单独走"预检→创建"流程；原路由不受任何影响。


@router.post("/_create_with_checks", response_model=Project)
async def create_project_with_checks(req: ProjectCreate) -> Project:
    """增强型创建：可配置 require_asset_preflight 触发预检阻塞。

    兼容保证：
    - req.require_asset_preflight=False（默认）时，行为与原 create_project 完全一致。
    - req.enable_preview_approval=False（默认）时，直接走全量 pipeline，与原逻辑一致。
    """
    if req.require_asset_preflight:
        pf = run_preflight(req)
        if not pf.passed:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "预检未通过，请修复下方 error 项后重试",
                    "preflight": pf.model_dump(),
                },
            )
    project = Project(
        id=f"proj_{uuid.uuid4().hex[:12]}",
        **req.model_dump(),
    )
    # 如果启用了预览审批：此时不立即进入队列，等前端调 /{id}/preview
    if project.enable_preview_approval:
        task_manager._projects[project.id] = project
        # 不 submit，留待前端 /preview 接口触发
        return project

    task_manager.submit(project)
    return project


# ───────────────── 4) 预览 + 审批流 ─────────────────


@router.post("/{project_id}/preview", response_model=Project)
async def run_preview_only(project_id: str):
    """只跑预览（15s 小样）→ 结束后状态 PREVIEWED，等 approve。"""
    project = task_manager.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if project.status not in {TaskStatus.PENDING, TaskStatus.REJECTED}:
        raise HTTPException(400, f"项目状态 {project.status} 无法重新预览（只能 PENDING/REJECTED 时触发）")
    # 覆盖预览模式参数（没开也强制开，毕竟用户显式调了这个 API）
    project.enable_preview_approval = True
    # 交给 task_manager 单独特化运行（preview_mode=True）
    task_manager.run_preview(project)
    return project


@router.post("/{project_id}/approve", response_model=Project)
async def approve_project(project_id: str, body: ProjectApproveRequest):
    """审批项目：approved=True → 批准，进入全量队列；False → 驳回。"""
    project = task_manager.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not body.approved:
        # 驳回（可再次 preview）
        project.status = TaskStatus.REJECTED
        project.error = body.reason or "人工驳回"
        # 推一条事件，让 SSE 订阅端感知
        task_manager._publish(TaskEvent(
            project_id=project_id,
            stage="approval",
            status=TaskStatus.REJECTED,
            message=body.reason or "人工驳回",
        ))
        return project

    # 批准：如果指定了 override_duration_sec 就覆盖
    if body.override_duration_sec:
        project.duration_sec = int(body.override_duration_sec)
    project.status = TaskStatus.APPROVED
    # 推事件
    task_manager._publish(TaskEvent(
        project_id=project_id,
        stage="approval",
        status=TaskStatus.APPROVED,
        progress=0.0,
        message=body.reason or "已批准，开始全量合成",
    ))
    # 丢入 task_manager 队列（preview_mode=False，全量）
    task_manager.submit_full(project)
    return project

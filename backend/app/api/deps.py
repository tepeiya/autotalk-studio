"""API 依赖。"""
from __future__ import annotations
from ...core.task_manager import task_manager

get_task_manager = lambda: task_manager

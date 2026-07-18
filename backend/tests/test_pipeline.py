"""冒烟测试：验证 Provider 注册、配置加载、Pipeline 导入正常。"""
import asyncio

import pytest


def test_provider_registry():
    from app.providers import registry
    providers = registry.list_providers()
    assert any(p["name"] == "openai" and p["type"] == "llm" for p in providers)
    assert any(p["name"] == "edge" and p["type"] == "tts" for p in providers)
    assert any(p["name"] == "musetalk" and p["type"] == "avatar" for p in providers)
    assert any(p["name"] == "bgm" and p["type"] == "media" for p in providers)


def test_settings_loads_defaults():
    from app.config import get_settings
    s = get_settings()
    assert s.host == "0.0.0.0"
    assert s.port == 8000
    assert s.llm.default_provider in ("openai", "ollama", "qwen")


def test_storage_init():
    from app.core.storage import get_storage
    storage = get_storage()
    assert storage.root.exists()
    assert storage.voices_dir.exists()


def test_pipeline_import():
    # 仅验证模块可导入，不实际执行
    from app.core.pipeline import Pipeline
    from app.core.schemas import Project, ProjectCreate, VideoOrientation
    p = Project(
        id="test",
        name="test",
        topic="测试主题",
        orientation=VideoOrientation.PORTRAIT,
    )
    pipe = Pipeline(p)
    assert pipe.project.id == "test"


def test_task_manager_init():
    from app.core.task_manager import task_manager
    assert task_manager.max_workers >= 1


def test_edge_tts_health():
    from app.providers.tts.edge_tts_provider import EdgeTTSProvider
    provider = EdgeTTSProvider()
    assert asyncio.get_event_loop().run_until_complete(provider.health_check())

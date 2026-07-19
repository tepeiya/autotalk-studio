"""Collector Provider 抽象 - 信息采集（Reddit/Twitter/HackerNews 等）。"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

from ..base import BaseProvider, registry


class BaseCollectorProvider(BaseProvider):
    type: str = "collector"

    @abstractmethod
    async def collect(self, source: str, limit: int = 5, **kwargs: Any) -> list[dict[str, Any]]:
        """采集热门内容。

        source: 数据源标识（如 subreddit 名）
        limit: 采集数量
        返回: 标准化的帖子列表（dict 字段：post_id/title/selftext/subreddit/author/score/...）
        """
        ...

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "source": {"type": "string", "description": "目标源（如 subreddit 名称）"},
            "limit": {"type": "int", "default": 5, "min": 1, "max": 50},
            "time_filter": {"type": "string", "default": "day", "options": ["hour", "day", "week", "month", "year", "all"]},
        }

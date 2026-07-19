"""Reddit 公开 .json 端点 Collector。

特点：
- 无需 Reddit API credentials（不用 PRAW）
- 直接 GET https://www.reddit.com/r/{subreddit}/top.json?t={time_filter}&limit={n}
- 用合理的 User-Agent 避免 429
- 失败时降级到 mock 数据
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from ..base import registry
from .base import BaseCollectorProvider

logger = logging.getLogger(__name__)

USER_AGENT = "AutoTalkStudio/0.1 (contact@autotalk.example) Python/httpx"

# 沙箱/无网降级用的 mock 帖子
_MOCK_POSTS = [
    {
        "post_id": "mock1",
        "title": "TIL that octopuses have three hearts and blue blood",
        "selftext": "Two of the hearts pump blood through the gills, while the third pumps it through the rest of the body. Their blood is blue because it contains copper-rich protein hemocyanin.",
        "subreddit": "todayilearned",
        "author": "octopus_fan",
        "score": 45200,
        "num_comments": 1289,
        "url": "",
        "permalink": "https://www.reddit.com/r/todayilearned/comments/mock1/",
        "created_utc": 1721000000.0,
    },
    {
        "post_id": "mock2",
        "title": "A 17-year-old built a working nuclear reactor in his garage",
        "selftext": "David Hahn attempted to build a breeder reactor in his backyard shed in 1994 using radioactive materials from smoke detectors and old glow-in-the-dark clocks. The EPA eventually had to clean up the site.",
        "subreddit": "interestingasfuck",
        "author": "science_nerd",
        "score": 38900,
        "num_comments": 2156,
        "url": "",
        "permalink": "https://www.reddit.com/r/interestingasfuck/comments/mock2/",
        "created_utc": 1721010000.0,
    },
    {
        "post_id": "mock3",
        "title": "Photographer captures the exact moment a lightning bolt hits the water",
        "selftext": "After 6 hours waiting during a storm, the photographer finally captured this incredible shot. The lightning formed a perfect tree-like structure spreading across the water surface.",
        "subreddit": "interestingasfuck",
        "author": "stormchaser",
        "score": 52100,
        "num_comments": 423,
        "url": "",
        "permalink": "https://www.reddit.com/r/interestingasfuck/comments/mock3/",
        "created_utc": 1721020000.0,
    },
    {
        "post_id": "mock4",
        "title": "This 100-year-old library in Japan has a track system that delivers books through pneumatic tubes",
        "selftext": "Built in 1923, the library still uses its original pneumatic tube system. Readers select a book from a catalog, push a button, and within 2 minutes the book arrives at their desk through a brass tube network.",
        "subreddit": "mildlyinteresting",
        "author": "library_lover",
        "score": 28700,
        "num_comments": 567,
        "url": "",
        "permalink": "https://www.reddit.com/r/mildlyinteresting/comments/mock4/",
        "created_utc": 1721030000.0,
    },
    {
        "post_id": "mock5",
        "title": "Scientists discover a new species of glowing shark in the deep ocean",
        "selftext": "The shark, named Etmopterus lailae, emits a blue-green glow from its belly. Researchers believe the bioluminescence helps it hunt in the dark depths of the Pacific Ocean, 1000 meters below the surface.",
        "subreddit": "natureismetal",
        "author": "deep_sea_explorer",
        "score": 33400,
        "num_comments": 892,
        "url": "",
        "permalink": "https://www.reddit.com/r/natureismetal/comments/mock5/",
        "created_utc": 1721040000.0,
    },
]


@registry.register
class RedditPublicCollector(BaseCollectorProvider):
    """通过 Reddit 公开 .json 端点采集。无需 API key。"""

    name = "reddit_public"

    def __init__(self, timeout: float = 15.0, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.timeout = timeout

    async def collect(self, source: str, limit: int = 5, **kwargs: Any) -> list[dict[str, Any]]:
        time_filter = kwargs.get("time_filter", "day")
        subreddit = source.strip().lstrip("/").lstrip("r/")
        url = f"https://www.reddit.com/r/{subreddit}/top.json?t={time_filter}&limit={limit}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("Reddit returned %s, falling back to mock", resp.status_code)
                    return self._fallback(subreddit, limit)
                data = resp.json()

            children = data.get("data", {}).get("children", [])
            posts: list[dict[str, Any]] = []
            for c in children:
                d = c.get("data", {})
                if not d.get("id"):
                    continue
                posts.append({
                    "post_id": d["id"],
                    "title": d.get("title", ""),
                    "selftext": (d.get("selftext") or "")[:3000],
                    "subreddit": d.get("subreddit", subreddit),
                    "author": d.get("author", "") or "",
                    "score": int(d.get("score", 0) or 0),
                    "num_comments": int(d.get("num_comments", 0) or 0),
                    "url": d.get("url", "") or "",
                    "permalink": "https://www.reddit.com" + (d.get("permalink", "") or ""),
                    "created_utc": float(d.get("created_utc", 0.0) or 0.0),
                })
            if not posts:
                logger.info("Reddit returned empty, using mock")
                return self._fallback(subreddit, limit)
            logger.info("Reddit collected %d posts from r/%s", len(posts), subreddit)
            return posts
        except Exception as e:
            logger.warning("Reddit collect failed (%s), using mock data", e)
            return self._fallback(subreddit, limit)

    def _fallback(self, subreddit: str, limit: int) -> list[dict[str, Any]]:
        posts = list(_MOCK_POSTS[:limit])
        # 替换 subreddit 为目标，模拟"该 subreddit 的内容"
        for p in posts:
            p = dict(p)
            p["subreddit"] = subreddit
        return [dict(p, subreddit=subreddit) for p in _MOCK_POSTS[:limit]]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": USER_AGENT}) as client:
                r = await client.get("https://www.reddit.com/r/test/top.json?limit=1")
                return r.status_code == 200
        except Exception:
            return False


@registry.register
class MockCollector(BaseCollectorProvider):
    """沙箱模式 Collector - 直接返回 mock 数据。"""

    name = "mock"
    requires_gpu = False

    async def collect(self, source: str, limit: int = 5, **kwargs: Any) -> list[dict[str, Any]]:
        await asyncio.sleep(0.1)
        return [dict(p, subreddit=source.strip().lstrip("r/")) for p in _MOCK_POSTS[:limit]]

    async def health_check(self) -> bool:
        return True

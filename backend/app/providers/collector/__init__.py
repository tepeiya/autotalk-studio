"""Collector Provider 包入口。"""
from . import base  # noqa: F401
from . import reddit_public_provider  # noqa: F401

__all__ = ["base", "reddit_public_provider"]

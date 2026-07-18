"""Providers 包：导入即注册。"""
from .base import BaseProvider, ProviderRegistry, registry  # noqa: F401
from . import llm  # noqa: F401
from . import tts  # noqa: F401
from . import avatar  # noqa: F401
from . import media  # noqa: F401
from . import publisher  # noqa: F401

__all__ = ["base", "llm", "tts", "avatar", "media", "publisher", "registry", "BaseProvider", "ProviderRegistry"]

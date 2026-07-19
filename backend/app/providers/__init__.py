"""Providers 包：导入即注册。"""
from .base import BaseProvider, ProviderRegistry, registry  # noqa: F401
from . import llm  # noqa: F401
from . import tts  # noqa: F401
from . import avatar  # noqa: F401
from . import media  # noqa: F401
from . import publisher  # noqa: F401
# Reddit 业务线新增 provider
from . import collector  # noqa: F401
from . import translator  # noqa: F401
from . import image  # noqa: F401
from . import note  # noqa: F401

__all__ = [
    "base", "llm", "tts", "avatar", "media", "publisher",
    "collector", "translator", "image", "note",
    "registry", "BaseProvider", "ProviderRegistry",
]

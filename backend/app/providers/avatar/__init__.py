"""数字人 Avatar Provider 包入口。"""
from . import base  # noqa: F401
from . import musetalk_provider  # noqa: F401
from . import wav2lip_provider  # noqa: F401
from . import heygem_provider  # noqa: F401
from . import mock_provider  # noqa: F401

__all__ = ["base", "musetalk_provider", "wav2lip_provider", "heygem_provider", "mock_provider"]

"""API 路由包。"""
from . import projects  # noqa: F401
from . import tasks  # noqa: F401
from . import voices  # noqa: F401
from . import avatars  # noqa: F401
from . import media  # noqa: F401
from . import publishers  # noqa: F401

__all__ = ["projects", "tasks", "voices", "avatars", "media", "publishers"]

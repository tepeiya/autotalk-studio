"""统一文件存储抽象。所有生成物（声音样本、数字人、视频、BGM）都走这里。"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from ..config import get_settings


class Storage:
    """按类别组织的本地存储。"""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().storage_path
        for sub in ("voices", "avatars", "bgm", "backgrounds", "videos", "tasks", "tmp"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    @property
    def voices_dir(self) -> Path:
        return self.root / "voices"

    @property
    def avatars_dir(self) -> Path:
        return self.root / "avatars"

    @property
    def bgm_dir(self) -> Path:
        return self.root / "bgm"

    @property
    def backgrounds_dir(self) -> Path:
        return self.root / "backgrounds"

    @property
    def videos_dir(self) -> Path:
        return self.root / "videos"

    @property
    def tasks_dir(self) -> Path:
        return self.root / "tasks"

    @property
    def tmp_dir(self) -> Path:
        return self.root / "tmp"

    def gen_id(self, prefix: str = "") -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short = uuid.uuid4().hex[:8]
        return f"{prefix}{ts}_{short}" if prefix else f"{ts}_{short}"

    def resolve(self, rel_or_abs: str | Path) -> Path:
        """允许传入相对/绝对路径，统一返回绝对路径。"""
        p = Path(rel_or_abs)
        if p.is_absolute():
            return p
        # 尝试相对 storage_root
        candidate = self.root / p
        if candidate.exists():
            return candidate
        return p

    def rel(self, abs_path: str | Path) -> str:
        """返回相对 storage_root 的路径，便于序列化。"""
        try:
            return str(Path(abs_path).resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(abs_path)

    def task_workspace(self, project_id: str) -> Path:
        ws = self.tasks_dir / project_id
        ws.mkdir(parents=True, exist_ok=True)
        return ws


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage

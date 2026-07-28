"""所有 Provider 的统一抽象基类。

设计要点：
- 每个具体能力（LLM / TTS / Avatar / Media / Publisher）都先继承 BaseProvider
- 各类型再有自己的子抽象类，定义本类型必需的方法
- Provider 通过名称注册，运行时按配置选择
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """所有 Provider 的根抽象。"""

    name: str = "base"
    type: str = "base"  # llm / tts / avatar / media / publisher
    requires_gpu: bool = False

    def __init__(self, **kwargs: Any) -> None:
        self.config: dict[str, Any] = kwargs

    @classmethod
    def _class_available(cls) -> bool:
        """同步可用性检查（用于列表页快速展示）。

        子类可覆盖：mock / media / 无需密钥的 provider 返回 True；
        需要 API Key / GPU / 外部依赖的类应显式返回 False 或做实际检查。
        """
        if cls.name == "mock" or "Mock" in cls.__name__:
            return True
        if cls.type == "media":
            return True
        # 默认：未配置的真实 provider 视为不可用
        return False

    @abstractmethod
    async def health_check(self) -> bool:
        """探测 Provider 是否可用。"""
        ...

    def get_config_schema(self) -> dict[str, Any]:
        """返回该 Provider 接受的配置项 schema（前端可用于动态渲染配置表单）。"""
        return {}

    def info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "requires_gpu": self.requires_gpu,
            "available": self._class_available(),
            "config_schema": self.get_config_schema(),
        }


class ProviderRegistry:
    """Provider 注册中心。"""

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseProvider]] = {}
        self._instances: dict[tuple[str, str], BaseProvider] = {}

    def register(self, provider_cls: type[BaseProvider]) -> type[BaseProvider]:
        """装饰器：注册一个 Provider 类。"""
        self._registry[f"{provider_cls.type}:{provider_cls.name}"] = provider_cls
        return provider_cls

    def list_providers(self, type_filter: str | None = None) -> list[dict[str, Any]]:
        result = []
        for key, cls in self._registry.items():
            ptype, pname = key.split(":", 1)
            if type_filter and ptype != type_filter:
                continue
            # 同步可用性判断：mock 类名 / name=mock / media 类型永远 True；
            # 真实 provider 默认 False（需用户配 API Key 或 GPU），可通过 _class_available 覆盖。
            try:
                available = cls._class_available()
            except Exception:
                available = (pname == "mock" or "Mock" in cls.__name__ or ptype in ("media",))
            result.append({
                "name": pname,
                "type": ptype,
                "requires_gpu": getattr(cls, "requires_gpu", False),
                "available": available,
                "config_schema": {},
                "class": cls.__name__,
            })
        return result

    def get_class(self, type_: str, name: str) -> type[BaseProvider]:
        key = f"{type_}:{name}"
        if key not in self._registry:
            raise KeyError(f"Provider not found: {key}")
        return self._registry[key]

    def create(self, type_: str, name: str, **kwargs: Any) -> BaseProvider:
        cls = self.get_class(type_, name)
        cache_key = (type_, name)
        if cache_key not in self._instances:
            self._instances[cache_key] = cls(**kwargs)
        return self._instances[cache_key]

    def create_fresh(self, type_: str, name: str, **kwargs: Any) -> BaseProvider:
        """每次创建新实例（用于需要传入运行时参数的 provider）。"""
        cls = self.get_class(type_, name)
        return cls(**kwargs)


# 全局注册中心实例
registry = ProviderRegistry()

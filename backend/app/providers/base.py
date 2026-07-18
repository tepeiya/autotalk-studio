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
            result.append({
                "name": pname,
                "type": ptype,
                "requires_gpu": getattr(cls, "requires_gpu", False),
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

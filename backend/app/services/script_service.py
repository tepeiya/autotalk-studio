"""Script Service - 台词生成服务，封装 LLM Provider 选择。"""
from __future__ import annotations

from ..config import get_settings
from ..core.schemas import ScriptRequest, ScriptResult
from ..providers.base import registry


class ScriptService:
    """统一 LLM 入口：根据配置/请求选择 Provider。"""

    async def generate(
        self,
        request: ScriptRequest,
        provider_name: str | None = None,
    ) -> ScriptResult:
        settings = get_settings()
        name = provider_name or settings.llm.default_provider
        provider = self._build(name)
        return await provider.generate_script(request)

    def _build(self, name: str):
        settings = get_settings()
        llm_cfg = settings.llm
        if name == "openai":
            return registry.create(
                "llm", "openai",
                api_key=llm_cfg.openai_api_key,
                base_url=llm_cfg.openai_base_url,
                model=llm_cfg.openai_model,
            )
        if name == "ollama":
            return registry.create(
                "llm", "ollama",
                base_url=llm_cfg.ollama_base_url,
                model=llm_cfg.ollama_model,
            )
        if name == "qwen":
            return registry.create(
                "llm", "qwen",
                api_key=llm_cfg.qwen_api_key,
                base_url=llm_cfg.qwen_base_url,
                model=llm_cfg.qwen_model,
            )
        if name == "mock":
            return registry.create("llm", "mock")
        raise ValueError(f"Unknown LLM provider: {name}")


script_service = ScriptService()

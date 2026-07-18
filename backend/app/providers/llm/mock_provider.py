"""Mock LLM Provider - 无需外部 API，用于演示和测试。"""
from __future__ import annotations

from ..base import registry
from .base import BaseLLMProvider
from ...core.schemas import ScriptRequest, ScriptResult, Shot


@registry.register
class MockLLMProvider(BaseLLMProvider):
    name = "mock"
    requires_gpu = False

    async def generate_script(self, request: ScriptRequest) -> ScriptResult:
        """返回一个固定的示例脚本，便于演示流水线。"""
        topic = request.topic
        shots = [
            Shot(
                index=1,
                text=f"大家好，今天来聊聊「{topic}」。",
                duration_sec=4.0,
                visual_prompt="开场镜头，主持人特写",
            ),
            Shot(
                index=2,
                text="第一点，保持专注，把手机放到看不见的地方。",
                duration_sec=5.0,
                visual_prompt="桌面手机被收走的画面",
            ),
            Shot(
                index=3,
                text="第二点，每天写日报，复盘今天做了什么。",
                duration_sec=5.0,
                visual_prompt="笔记本上写日报",
            ),
            Shot(
                index=4,
                text="第三点，善用 AI 工具，让重复劳动自动化。",
                duration_sec=5.0,
                visual_prompt="AI 工具界面",
            ),
            Shot(
                index=5,
                text="第四点，固定作息，规律比天赋更重要。",
                duration_sec=5.0,
                visual_prompt="作息时间表",
            ),
            Shot(
                index=6,
                text="第五点，多分享，教别人是最好的学。",
                duration_sec=5.0,
                visual_prompt="分享场景",
            ),
            Shot(
                index=7,
                text="以上五点，希望对你有帮助。关注我，下期见！",
                duration_sec=4.0,
                visual_prompt="结尾镜头，主持人挥手",
            ),
        ]
        return ScriptResult(
            title=f"5 个让你效率翻倍的程序员习惯 - {topic}",
            full_text=" ".join(s.text for s in shots),
            shots=shots,
            tags=["效率", "程序员", "习惯"],
        )

    async def _ping(self) -> None:
        return None

    async def health_check(self) -> bool:
        return True

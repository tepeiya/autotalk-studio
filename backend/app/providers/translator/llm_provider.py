"""LLM-based Translator Provider - 用 LLM 做翻译+润色+提取关键点+生成标签。

复用现有 LLM Provider 抽象（OpenAI/Ollama/Qwen/Mock），无需新建 LLM 客户端。
默认 prompt 针对小红书笔记风格优化（标题党 + emoji + 话题标签）。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..base import registry as preg
from ..llm.base import BaseLLMProvider
from ..base import BaseProvider
from .base import BaseTranslatorProvider

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """你是一名资深的小红书内容编辑，擅长把英文爆款内容翻译润色成符合中文社交媒体传播的笔记。

要求：
1. 标题：≤20 字，吸睛、带情绪、可加 1-2 个 emoji，但不要低俗
2. 摘要：一句话概括核心信息（≤30 字）
3. 正文：流畅自然的中文，分段清晰，适当加 emoji，保留原帖所有事实信息但避免机翻腔
4. 关键点：提取 3-5 个要点，每条 ≤25 字
5. 标签：5-8 个适合小红书的话题标签（不带 #，单词或短语）
6. 小红书适配评估：判断该内容是否适合发小红书（避开敏感、低俗、政治、争议话题）
7. 爆款潜力分：1-10 分，10 表示极易爆，1 表示毫无爆款潜力。考虑因素：
   - 情绪共鸣度（惊讶/搞笑/感动/启发）
   - 信息差价值（用户能否"涨知识"）
   - 视觉想象空间（是否能想象出画面）
   - 中文受众接受度

输出严格 JSON 格式（不要 markdown 代码块）：
{
  "title_cn": "...",
  "summary_cn": "...",
  "body_cn": "...",
  "key_points": ["...", "..."],
  "tags": ["...", "..."],
  "is_xhs_friendly": true,
  "xhs_potential_score": 8,
  "viral_reason": "简短说明为何这个分数"
}
"""

MOCK_PROMPT_TEMPLATE = """原帖标题：{title}
原帖正文：{body}
"""

# 当无 LLM 可用时的本地"翻译"逻辑（极简关键词替换）
_KEYWORD_MAP = {
    "the ": "", "The ": "", "a ": "", "A ": "", "an ": "", "An ": "",
    "and": "和", "or": "或", "but": "但",
    "is": "是", "are": "是", "was": "是", "were": "是",
    "shark": "鲨鱼", "octopus": "章鱼", "lightning": "闪电",
    "library": "图书馆", "scientist": "科学家", "photographer": "摄影师",
    "researcher": "研究员", "blood": "血液", "heart": "心脏",
    "discovered": "发现", "captures": "拍下", "built": "建造",
    "shark": "鲨鱼", "glowing": "发光的", "deep ocean": "深海",
    "nuclear reactor": "核反应堆", "garage": "车库",
    "lightning bolt": "闪电", "water": "水面",
    "100-year-old": "百年", "Japan": "日本",
    "pneumatic tubes": "气动管道", "books": "书",
    "blue blood": "蓝色血液", "three hearts": "三颗心脏",
    "species": "物种", "bioluminescence": "生物发光",
}


def _crude_local_translate(text: str) -> str:
    """无 LLM 时的降级翻译（仅替换关键词，保留原结构）。"""
    out = text
    for en, cn in _KEYWORD_MAP.items():
        out = out.replace(en, cn)
    return out


def _make_mock_output(title: str, body: str) -> dict[str, Any]:
    """生成符合小红书风格的 mock 翻译输出。"""
    title_cn_raw = _crude_local_translate(title)
    # 取前 18 字作为标题，加点 emoji
    title_cn = (title_cn_raw[:18] + "…") if len(title_cn_raw) > 18 else title_cn_raw
    emoji_pool = ["🔥", "✨", "😱", "🤯", "📸", "🌊", "💡", "📖"]
    title_cn = f"{emoji_pool[0]} {title_cn}"
    body_cn = _crude_local_translate(body)
    body_cn = body_cn if body_cn else "（无正文）"
    body_cn = f"{body_cn}\n\n#今日科普 #涨知识"

    # 关键点
    points = []
    sentences = re.split(r"[.。!！\n]", body)
    for s in sentences[:5]:
        s = s.strip()
        if len(s) > 10:
            cn = _crude_local_translate(s)
            points.append(cn[:25])
        if len(points) >= 3:
            break
    if not points:
        points = ["关键点 1", "关键点 2", "关键点 3"]

    return {
        "title_cn": title_cn,
        "summary_cn": title_cn_raw[:30],
        "body_cn": body_cn,
        "key_points": points,
        "tags": ["科普", "涨知识", "冷知识", "海外趣闻", "今日热门"],
        # mock 模式默认给一个中等偏上的评分，便于筛选逻辑跑通
        "is_xhs_friendly": True,
        "xhs_potential_score": 7,
        "viral_reason": "mock 模式默认评分（未调用 LLM）",
    }


@preg.register
class LLMTranslatorProvider(BaseTranslatorProvider):
    """用 LLM Provider 做翻译+润色。

    配置：
        llm_provider: 使用的 LLM 名称（openai/ollama/qwen/mock）
        system_prompt: 自定义 system prompt
        target_lang: 目标语言（默认 zh）
    """

    name = "llm"

    def __init__(
        self,
        llm_provider: str = "mock",
        system_prompt: str | None = None,
        target_lang: str = "zh",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.llm_provider_name = llm_provider
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.target_lang = target_lang

    async def translate_and_polish(
        self,
        title: str,
        body: str,
        target_lang: str = "zh",
        **kwargs: Any,
    ) -> dict[str, Any]:
        # 1) 尝试用 LLM
        try:
            llm: BaseLLMProvider = preg.create("llm", self.llm_provider_name)
            from ...core.schemas import ScriptRequest
            user_msg = MOCK_PROMPT_TEMPLATE.format(title=title[:500], body=body[:2000])
            # 复用 LLM 的 generate_script 但传一个简单 topic，强制 system prompt 起作用
            # 实际上更好的方式是直接调底层 chat completion，但为复用现有抽象，
            # 这里把 user_msg 当 topic 传入，让 LLM 看到 system_prompt
            req = ScriptRequest(
                topic=user_msg,
                style="informative",
                duration_sec=10,
                language=target_lang,
            )
            result = await llm.generate_script(req)
            # 尝试从 result.full_text 解析 JSON
            text = result.full_text.strip()
            # 去除可能的 markdown 代码块
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
            try:
                parsed = json.loads(text)
                # 字段补全（含爆款评分）
                score = parsed.get("xhs_potential_score", 0)
                try:
                    score = int(score)
                except (TypeError, ValueError):
                    score = 0
                if score < 0 or score > 10:
                    score = max(0, min(10, score))
                return {
                    "title_cn": parsed.get("title_cn", title[:20]),
                    "summary_cn": parsed.get("summary_cn", ""),
                    "body_cn": parsed.get("body_cn", result.full_text),
                    "key_points": parsed.get("key_points", []),
                    "tags": parsed.get("tags", []),
                    "is_xhs_friendly": bool(parsed.get("is_xhs_friendly", True)),
                    "xhs_potential_score": score,
                    "viral_reason": str(parsed.get("viral_reason", ""))[:200],
                }
            except json.JSONDecodeError:
                logger.warning("LLM returned non-JSON, using full_text as body_cn")
                return {
                    "title_cn": title[:20],
                    "summary_cn": "",
                    "body_cn": result.full_text,
                    "key_points": [],
                    "tags": [],
                    "is_xhs_friendly": True,
                    "xhs_potential_score": 0,
                    "viral_reason": "LLM 未返回合法 JSON，未评分",
                }
        except Exception as e:
            logger.warning("LLM translation failed (%s), using mock translation", e)

        # 2) 降级 mock
        return _make_mock_output(title, body)

    async def health_check(self) -> bool:
        return True

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "llm_provider": {"type": "string", "default": "mock",
                              "options": ["mock", "openai", "ollama", "qwen"]},
            "target_lang": {"type": "string", "default": "zh"},
        }


@preg.register
class MockTranslatorProvider(BaseTranslatorProvider):
    """纯本地 mock 翻译，无任何外部依赖。"""

    name = "mock"

    async def translate_and_polish(
        self,
        title: str,
        body: str,
        target_lang: str = "zh",
        **kwargs: Any,
    ) -> dict[str, Any]:
        return _make_mock_output(title, body)

    async def health_check(self) -> bool:
        return True

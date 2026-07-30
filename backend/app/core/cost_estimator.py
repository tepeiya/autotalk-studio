"""费用估算模块（借鉴 Rachel Skill：付费API调用前先算个大概）。

注意：所有单价都是"经验估测"，实际以服务商账单为准。
- 本地 / Mock Provider 单价一律为 0
- 海外 SaaS 按美元兑人民币 7.25 粗略换算
"""
from __future__ import annotations

import logging

from .schemas import (
    CostEstimateItem,
    CostEstimateResult,
    ProjectCreate,
    Project,
)
from ..config import get_settings

logger = logging.getLogger(__name__)

# ─────────────────── 粗略单价表（单位：人民币 元，仅供参考） ───────────────────
# LLM：按 1k tokens 计算（输入≈输出各半粗略估算）
LLM_PRICE_PER_1K_TOKENS = {
    "openai": {"gpt-4o-mini": 0.018, "gpt-4o": 0.25, "default": 0.05},
    "qwen":  {"qwen-plus": 0.008, "qwen-max": 0.04, "default": 0.01},
    "ollama": {"default": 0.0},
    "mock":   {"default": 0.0},
}

# TTS：按秒计算（本地部署一律 0）
TTS_PRICE_PER_SECOND = {
    "edge":      0.0,
    "cosyvoice": 0.0,
    "gptsovits": 0.0,
    "indextts":  0.0,
    "mock":      0.0,
}

# Avatar：按秒计算（SaaS HeyGen ≈ 0.4 元/分钟 ≈ 0.0067/s；本地 GPU 视为 0，只算电费忽略）
AVATAR_PRICE_PER_SECOND = {
    "musetalk":  0.0,   # 本地 GPU 部署
    "wav2lip":   0.0,
    "heygem":    0.0,
    "mock":      0.0,
}

# Publisher：按 1 次发布计算（纯自动化不计额外成本）
PUBLISHER_PRICE_PER_CALL = {
    "dummy":                0.0,
    "social_auto_upload":   0.0,   # 自家浏览器自动化，只算时间
}

# 默认字符→token 换算：中文 1 token ≈ 1.5 字；英文 1 token ≈ 4 字符；粗估平均值用 1.8
CHAR_PER_TOKEN = 1.8
SHOT_MIN_CHARS = 30  # 每分镜最少 30 字输出估算


def estimate_cost(req: ProjectCreate | Project) -> CostEstimateResult:
    """估算单项目成本（不调用网络、不扣额度）。"""
    items: list[CostEstimateItem] = []
    settings = get_settings()

    llm_prov = (req.llm_provider or settings.llm.default_provider).lower()
    tts_prov = (req.tts_provider or settings.tts.default_provider).lower()
    av_prov  = (req.avatar_provider or settings.avatar.default_provider).lower()

    # ────────── 1. LLM 文案生成 ──────────
    # 估算输出 tokens：按 duration_sec * 每秒 3 字 / CHAR_PER_TOKEN
    estimated_chars = max(SHOT_MIN_CHARS * 6, int(req.duration_sec) * 3 + 200)
    estimated_tokens = estimated_chars / CHAR_PER_TOKEN * 1.5  # 1.5x 含 prompt+padding
    price_table = LLM_PRICE_PER_1K_TOKENS.get(llm_prov, LLM_PRICE_PER_1K_TOKENS["mock"])
    model_key = {
        "openai": settings.llm.openai_model,
        "qwen":   settings.llm.qwen_model,
        "ollama": settings.llm.ollama_model,
    }.get(llm_prov, "default") or "default"
    unit_price_1k = price_table.get(model_key, price_table.get("default", 0.0))
    llm_cost = (estimated_tokens / 1000) * unit_price_1k
    note = None
    if llm_prov in {"mock", "ollama"}:
        note = "本地/Mock，无直接费用"
    items.append(CostEstimateItem(
        provider=f"llm-{llm_prov}", stage="script", unit="tokens",
        estimated_units=round(estimated_tokens, 2),
        unit_cost_cny=round(unit_price_1k / 1000, 6),
        estimated_cost_cny=round(llm_cost, 4),
        note=note,
    ))

    # ────────── 2. TTS 语音合成 ──────────
    tts_sec = float(req.duration_sec)
    tts_unit_price = TTS_PRICE_PER_SECOND.get(tts_prov, 0.0)
    tts_cost = tts_sec * tts_unit_price
    note = None
    if tts_prov in {"edge", "cosyvoice", "gptsovits", "indextts", "mock"}:
        note = "免费或本地部署，无直接费用"
    items.append(CostEstimateItem(
        provider=f"tts-{tts_prov}", stage="voice", unit="seconds",
        estimated_units=round(tts_sec, 2),
        unit_cost_cny=round(tts_unit_price, 6),
        estimated_cost_cny=round(tts_cost, 4),
        note=note,
    ))

    # ────────── 3. Avatar 数字人口播 ──────────
    if req.avatar_id:
        av_sec = tts_sec
        av_unit_price = AVATAR_PRICE_PER_SECOND.get(av_prov, 0.0)
        av_cost = av_sec * av_unit_price
        note = None
        if av_prov in {"musetalk", "wav2lip", "heygem", "mock"}:
            note = "本地 GPU / Mock，无直接 SaaS 费用（仅消耗 GPU 电力）"
        items.append(CostEstimateItem(
            provider=f"avatar-{av_prov}", stage="avatar", unit="seconds",
            estimated_units=round(av_sec, 2),
            unit_cost_cny=round(av_unit_price, 6),
            estimated_cost_cny=round(av_cost, 4),
            note=note,
        ))

    # ────────── 4. 发布（按平台数计次）──────────
    if req.auto_publish and req.publish_platforms:
        plat_count = len(req.publish_platforms)
        publish_cost = 0.0
        # "dummy" 算 0；其他一律按 social_auto_upload 计 0 元（自家自动化）
        for plat in req.publish_platforms:
            provider_name = "dummy" if plat == "dummy" else "social_auto_upload"
            publish_cost += PUBLISHER_PRICE_PER_CALL.get(provider_name, 0.0)
        items.append(CostEstimateItem(
            provider="publisher-social_auto_upload", stage="publish", unit="calls",
            estimated_units=float(plat_count),
            unit_cost_cny=0.0,
            estimated_cost_cny=round(publish_cost, 4),
            note="自家浏览器自动化，无 SaaS 费用（仅本机资源/账号风控）",
        ))

    total = round(sum(x.estimated_cost_cny for x in items), 4)

    if total == 0:
        summary = "预估总花费 0 元（当前配置全部是本地/Mock/免费方案）✅"
        confidence = "exact"
    elif total < 0.5:
        summary = f"预估总花费约 {total:.3f} 元，几乎可以忽略，真实以服务商账单为准"
        confidence = "rough"
    else:
        summary = f"预估总花费约 {total:.2f} 元（仅供参考，实际费用受服务商定价、模型版本、token 数影响）"
        confidence = "rough"

    return CostEstimateResult(
        items=items,
        total_cny=total,
        currency="CNY",
        confidence=confidence,
        summary=summary,
    )

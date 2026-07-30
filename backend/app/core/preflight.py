"""资产预检模块（借鉴 Rachel Skill 的 preflight_assets.py 思想）。

核心原则：
- 对运行时 ProjectCreate / Project 做"静态体检"，不产生任何副作用
  （不调用 LLM/TTS/Avatar、不写文件、不消耗 API 额度）
- 报告用 error / warning / info 三级分类
- require_asset_preflight=False（默认）时，预检不通过也不阻塞运行；
  只有开启 require_asset_preflight=True 才会强制不通过就不执行。
"""
from __future__ import annotations

import logging
from pathlib import Path

from .schemas import (
    PreflightIssue,
    PreflightResult,
    ProjectCreate,
    Project,
)
from ..config import get_settings
from ..services.avatar_service import avatar_service
from ..services.media_service import media_service
from ..services.voice_service import voice_service

logger = logging.getLogger(__name__)


def run_preflight(req: ProjectCreate | Project) -> PreflightResult:
    """对项目参数做资产预检，返回结构化报告。"""
    issues: list[PreflightIssue] = []

    # ────────── 1. 必填字段 & 基本合理性 ──────────
    if not req.topic or not req.topic.strip():
        issues.append(PreflightIssue(
            level="error", code="EMPTY_TOPIC", field="topic",
            message="项目 topic/主题为空，LLM 无法生成文案。",
        ))
    if not (10 <= int(req.duration_sec) <= 600):
        issues.append(PreflightIssue(
            level="error", code="DURATION_OOR", field="duration_sec",
            message=f"时长 {req.duration_sec}s 超出范围（10~600s）",
        ))
    if req.duration_sec > 300:
        issues.append(PreflightIssue(
            level="warning", code="DURATION_TOO_LONG", field="duration_sec",
            message=f"时长 {req.duration_sec}s 较长（>5 分钟），建议切分，避免 API 费用超支",
        ))
    if req.enable_preview_approval and not (5 <= int(req.preview_duration_sec) <= 60):
        issues.append(PreflightIssue(
            level="warning", code="PREVIEW_DURATION_OOR", field="preview_duration_sec",
            message=f"预览时长 {req.preview_duration_sec}s 建议在 5~60s 区间",
        ))

    # ────────── 2. LLM / TTS / Avatar 资产是否就绪（静态判断，不扣额度） ──────────
    llm_prov = (req.llm_provider or get_settings().llm.default_provider).lower()
    tts_prov = (req.tts_provider or get_settings().tts.default_provider).lower()
    av_prov = (req.avatar_provider or get_settings().avatar.default_provider).lower()

    # LLM 层：本地 Ollama / Mock 始终算 OK；其他（OpenAI / Qwen）只做"有环境变量即 OK"，不打网络
    if llm_prov in {"qwen"}:
        if not get_settings().llm.qwen_api_key:
            issues.append(PreflightIssue(
                level="error", code="LLM_QWEN_KEY_MISSING", field="llm_provider",
                message="默认/选择的 LLM 为 qwen，但未配置 QWEN_API_KEY",
            ))
    elif llm_prov in {"openai"}:
        if not (get_settings().llm.openai_api_key or get_settings().llm.openai_base_url):
            issues.append(PreflightIssue(
                level="error", code="LLM_OPENAI_KEY_MISSING", field="llm_provider",
                message="默认/选择的 LLM 为 openai，但未配置 OPENAI_API_KEY/BASE_URL",
            ))
    elif llm_prov in {"mock", "ollama"}:
        issues.append(PreflightIssue(
            level="info", code="LLM_LOCAL_OR_MOCK", field="llm_provider",
            message=f"LLM 为 {llm_prov}，无需 API Key（Mock 或本地）",
        ))

    # TTS：Edge / Mock 始终 OK；其他（CosyVoice / GPT-SoVITS / IndexTTS）判断 URL 是否可访问就算了——这里静态只判断非空
    if tts_prov == "edge":
        issues.append(PreflightIssue(
            level="info", code="TTS_EDGE_FREE", field="tts_provider",
            message="TTS 为 Edge-TTS，完全免费可用",
        ))
    elif tts_prov == "mock":
        pass
    else:
        # 只检查对应 base_url 有没有填
        tts_sett = get_settings().tts
        url = {
            "cosyvoice": tts_sett.cosyvoice_base_url,
            "gptsovits": tts_sett.gptsovits_base_url,
            "indextts": tts_sett.indextts_base_url,
        }.get(tts_prov)
        if not url:
            issues.append(PreflightIssue(
                level="warning", code="TTS_BASE_URL_EMPTY", field="tts_provider",
                message=f"TTS Provider {tts_prov} 未配置 base_url，可能会失败",
            ))
    # voice_id：TTS 非 Mock 时，若有 voice_id 做一次静态存在性检查
    if req.voice_id and tts_prov != "mock":
        try:
            vp = voice_service.get_profile(req.voice_id)
            if vp is None:
                issues.append(PreflightIssue(
                    level="warning", code="VOICE_ID_NOT_FOUND", field="voice_id",
                    message=f"voice_id={req.voice_id} 不存在，合成时会回退默认发音人",
                ))
        except Exception:
            pass

    # Avatar：若用户指定了 avatar_id 才检查；没指定就算纯图文也没问题
    if req.avatar_id:
        try:
            ap = avatar_service.get_profile(req.avatar_id)
            if ap is None:
                issues.append(PreflightIssue(
                    level="error", code="AVATAR_ID_NOT_FOUND", field="avatar_id",
                    message=f"avatar_id={req.avatar_id} 不存在，请先在 Avatar Studio 注册",
                ))
            else:
                # 检查 portrait_path 存在
                if not Path(ap.portrait_path).exists():
                    issues.append(PreflightIssue(
                        level="error", code="AVATAR_PORTRAIT_MISSING", field="avatar_id",
                        message=f"人像图 {ap.portrait_path} 文件不存在，数字人口播会失败",
                    ))
        except Exception as e:
            logger.debug("avatar preflight check skipped: %s", e)
    else:
        issues.append(PreflightIssue(
            level="info", code="NO_AVATAR_SELECTED", field="avatar_id",
            message="未选择数字人 avatar，将使用背景 + 配音模式（无口播人像）",
        ))

    # Avatar Provider 本地/GPU 部署提示
    if av_prov in {"musetalk", "wav2lip", "heygem"}:
        av_sett = get_settings().avatar
        av_url = {
            "musetalk": av_sett.musetalk_base_url,
            "wav2lip": av_sett.wav2lip_base_url,
            "heygem": av_sett.heygem_base_url,
        }.get(av_prov)
        if not av_url:
            issues.append(PreflightIssue(
                level="warning", code="AVATAR_BASE_URL_EMPTY", field="avatar_provider",
                message=f"Avatar {av_prov} 未配置 base_url（GPU 服务地址），口播将失败或回退 Mock",
            ))

    # ────────── 3. Media 资产（BGM / 背景）数量静态检查 ──────────
    try:
        bgm_items = media_service.list_bgm()
        bg_items = media_service.list_backgrounds()
        if req.bgm_mode != "none":
            if len(bgm_items) == 0:
                issues.append(PreflightIssue(
                    level="warning", code="NO_BGM_FILES", field="bgm_mode",
                    message="启用 BGM 但 storage/bgm 目录为空，建议先到 Media Library 上传",
                ))
        if req.bg_mode != "none":
            if len(bg_items) == 0:
                issues.append(PreflightIssue(
                    level="warning", code="NO_BG_FILES", field="bg_mode",
                    message="启用背景但 storage/backgrounds 目录为空，会使用纯色占位视频",
                ))
    except Exception:
        pass

    # ────────── 4. 发布平台静态检查 ──────────
    if req.auto_publish:
        if not req.publish_platforms:
            issues.append(PreflightIssue(
                level="warning", code="PUBLISH_ENABLED_BUT_NO_PLATFORMS", field="publish_platforms",
                message="已开自动发布，但 publish_platforms 为空，会跳过发布阶段",
            ))
        for plat in req.publish_platforms:
            if plat == "dummy":
                issues.append(PreflightIssue(
                    level="info", code="PUBLISHER_DUMMY", field="publish_platforms",
                    message="使用 dummy Publisher，仅模拟，不会真实发布",
                ))

    # ────────── 汇总统计 ──────────
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    infos = [i for i in issues if i.level == "info"]

    # require_asset_preflight=False（默认）时，即便有 error，仍"不阻塞"——只是报告
    # 真正的"阻塞与否"由调用方（POST /projects 或 task_manager.submit）自行判断
    if req.require_asset_preflight:
        passed = len(errors) == 0
    else:
        passed = True  # 非强制模式，任何情况都能过

    if errors:
        summary = f"预检发现 {len(errors)} 个错误 / {len(warnings)} 个警告"
    elif warnings:
        summary = f"预检通过，仅有 {len(warnings)} 个警告项"
    else:
        summary = "预检全部通过 ✅"

    return PreflightResult(
        passed=passed,
        summary=summary,
        issues=issues,
        error_count=len(errors),
        warning_count=len(warnings),
        info_count=len(infos),
    )

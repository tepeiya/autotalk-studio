"""Voice Service - 声音克隆 + TTS 合成。"""
from __future__ import annotations

from pathlib import Path

from ..config import get_settings
from ..core.schemas import SynthesizeRequest, VoiceProfile
from ..core.storage import get_storage
from ..providers.base import registry


class VoiceService:
    """管理声音克隆与语音合成。"""

    async def clone(
        self,
        sample_path: Path,
        name: str,
        provider_name: str | None = None,
    ) -> VoiceProfile:
        settings = get_settings()
        pname = provider_name or settings.tts.default_provider
        provider = self._build(pname)

        # 复制样本到 storage/voices/
        storage = get_storage()
        sample = storage.voices_dir / f"{name}_sample{sample_path.suffix}"
        sample.write_bytes(sample_path.read_bytes())

        voice_id = await provider.clone_voice(sample, name)
        profile = VoiceProfile(
            id=storage.gen_id("voice_"),
            name=name,
            provider=pname,
            sample_path=str(sample),
        )
        # 持久化元信息（简化：写 json 文件）
        meta = storage.voices_dir / f"{profile.id}.json"
        meta.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        # 把内部 voice_id 也存下来供后续合成用
        meta.with_suffix(".voice_id.txt").write_text(voice_id, encoding="utf-8")
        return profile

    async def synthesize(
        self,
        request: SynthesizeRequest,
        provider_name: str | None = None,
    ) -> Path:
        settings = get_settings()
        pname = provider_name or settings.tts.default_provider
        provider = self._build(pname)

        # 解析内部 voice_id：优先读 storage/voices/{voice_id}.voice_id.txt
        storage = get_storage()
        voice_id_file = storage.voices_dir / f"{request.voice_id}.voice_id.txt"
        internal_id = request.voice_id
        if voice_id_file.exists():
            internal_id = voice_id_file.read_text(encoding="utf-8").strip() or request.voice_id

        output_path = storage.tmp_dir / f"{storage.gen_id('tts_')}.mp3"
        return await provider.synthesize(
            text=request.text,
            voice_id=internal_id,
            output_path=output_path,
            speed=request.speed,
            pitch=request.pitch,
        )

    def list_voices(self) -> list[VoiceProfile]:
        storage = get_storage()
        result = []
        for p in storage.voices_dir.glob("*.json"):
            try:
                result.append(VoiceProfile.model_validate_json(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return result

    async def list_provider_voices(self, provider_name: str | None = None) -> list[dict]:
        settings = get_settings()
        pname = provider_name or settings.tts.default_provider
        provider = self._build(pname)
        return await provider.list_voices()

    def _build(self, name: str):
        settings = get_settings()
        cfg = settings.tts
        if name == "edge":
            return registry.create("tts", "edge", voice=cfg.edge_voice)
        if name == "cosyvoice":
            return registry.create("tts", "cosyvoice", base_url=cfg.cosyvoice_base_url)
        if name == "gptsovits":
            return registry.create("tts", "gptsovits", base_url=cfg.gptsovits_base_url)
        if name == "indextts":
            return registry.create("tts", "indextts", base_url=cfg.indextts_base_url)
        raise ValueError(f"Unknown TTS provider: {name}")


voice_service = VoiceService()

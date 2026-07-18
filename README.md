<div align="center">

<h1>AutoTalk Studio</h1>

<p align="center">
  <strong>AI 数字人口播视频自动生产系统</strong><br>
  一句话主题 → AI 生成台词 → 声音克隆 → 数字人口播 → 自动换背景/BGM → 批量出片 → 多平台发布
</p>

<p align="center">
  <a href="https://github.com/tepeiya/autotalk-studio/actions"><img alt="CI" src="https://github.com/tepeiya/autotalk-studio/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/tepeiya/autotalk-studio"><img alt="Stars" src="https://img.shields.io/github/stars/tepeiya/autotalk-studio?style=social"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/tepeiya/autotalk-studio"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="Vue" src="https://img.shields.io/badge/vue-3.4-42b883">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688">
  <img alt="Status" src="https://img.shields.io/badge/status-WIP-orange">
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#集成来源">集成来源</a> ·
  <a href="#系统架构">架构</a> ·
  <a href="#provider-扩展">Provider 扩展</a> ·
  <a href="#路线图">路线图</a> ·
  <a href="PLAN.md">设计文档</a>
</p>

</div>

---

## 集成来源

本系统借鉴下列优秀开源项目的能力组合而成：

| 能力 | 借鉴项目 |
|---|---|
| AI 自动生成台词 | Pixelle-Video / MoneyPrinterTurbo |
| 声音克隆 TTS | GPT-SoVITS / CosyVoice / IndexTTS / 元界AI |
| 数字人口播合成 | MuseTalk / Wav2Lip / HeyGem / AigcPanel |
| 背景与音乐自动切换 | Pixelle-Video / MoneyPrinterTurbo |
| 批量任务调度 | LuoGen-agent / MoneyPrinterTurbo |
| 多平台发布 | LuoGen-agent / 元界AI |
| 模块化可替换 | Pixelle-Video ComfyUI 架构 |

架构设计详见 [PLAN.md](./PLAN.md)。

## 快速开始

### 1. 后端

```bash
cd backend
cp .env.example .env        # 填入 API key
pip install -e .            # 或 uv sync
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看接口。

### 2. 前端

```bash
cd frontend
npm install
npm run dev                # http://localhost:5173
```

### 3. Docker 一键启动

```bash
cp config/config.example.yaml config/config.yaml
docker compose up -d
```

## 系统要求

- Python 3.10–3.12
- Node.js 18+
- ffmpeg（系统 PATH 中）

### 可选（启用高级能力）

- **本地 LLM**：[Ollama](https://ollama.com/) 运行 `qwen2.5:7b` 等模型
- **声音克隆**：自部署 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) / [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) / [IndexTTS](https://github.com/index-tts/index-tts)
- **数字人**：自部署 [MuseTalk](https://github.com/TMElyralab/MuseTalk) / [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) / [HeyGem](https://github.com/duixcom/Duix-Heygem)

不部署这些也能跑：默认 Edge-TTS 零配置可用，LLM 用 OpenAI 或本地 Ollama 即可。

## 目录结构

```
/workspace
├── PLAN.md                 # 架构设计
├── README.md
├── docker-compose.yml
├── config/
│   ├── config.example.yaml
│   └── prompts/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/routes/     # 6 个路由
│   │   ├── core/           # schemas / pipeline / task_manager / storage
│   │   ├── providers/      # LLM/TTS/Avatar/Media/Publisher Provider
│   │   ├── services/       # 5 个业务 service
│   │   └── utils/
│   └── tests/
├── frontend/               # Vue3 + Vite + Element Plus
│   └── src/
│       ├── api/client.ts
│       ├── stores/         # Pinia
│       ├── views/          # 7 个页面
│       └── components/layout/
└── storage/                # 运行时生成（gitignored）
```

## 核心 API

| 路径 | 说明 |
|---|---|
| `POST /api/projects` | 创建并提交项目（一句话出片） |
| `GET /api/projects/{id}` | 查询项目状态与进度 |
| `GET /api/tasks/{id}/stream` | SSE 实时进度流 |
| `POST /api/voices/clone` | 声音克隆 |
| `POST /api/voices/synthesize` | TTS 合成 |
| `POST /api/avatars/register` | 注册数字人形象 |
| `POST /api/avatars/render` | 渲染口播视频 |
| `GET /api/media/bgm` | BGM 列表 |
| `GET /api/providers` | 已注册 Provider 列表 |

完整文档见 `/docs`。

## 工作流程

```
用户创建 Project(topic=xxx)
        │
        ▼
[ScriptService] LLM 生成文案 + 拆分镜
        │
        ▼
[VoiceService] 每分镜用克隆音色 TTS
        │   并行
[MediaService] 每分镜选背景图 + BGM
        │
        ▼
[AvatarService] 每分镜驱动数字人口播
        │
        ▼
[VideoService] ffmpeg 拼接 + 混 BGM → 成片
        │
        ▼
[Publisher] (可选) 发布到抖音/B站/快手
```

## Provider 扩展

新增一个 Provider 只需：

1. 在 `app/providers/{type}/` 下新建文件
2. 继承对应基类（如 `BaseTTSProvider`）
3. 用 `@registry.register` 装饰类

```python
from ..base import registry
from .base import BaseTTSProvider

@registry.register
class MyTTSProvider(BaseTTSProvider):
    name = "my_tts"
    async def synthesize(self, ...):
        ...
```

无需改动其他代码，前端 `/api/providers` 自动列出。

## 路线图

- [x] 完整架构 + 框架代码
- [x] LLM：OpenAI / Ollama / Qwen
- [x] TTS：Edge-TTS（默认可用）+ CosyVoice / GPT-SoVITS / IndexTTS 接口
- [x] Avatar：MuseTalk / Wav2Lip / HeyGem 接口
- [x] Media：BGM + 背景库
- [x] Pipeline 编排 + 批量任务 + SSE
- [x] Vue3 前端骨架 + 7 个页面
- [ ] ComfyUI 工作流接入（参考 Pixelle-Video）
- [ ] 真实多平台发布 SDK 接入
- [ ] 分布式任务队列（Celery + Redis）
- [ ] ASR 粗剪 / AI 转场（参考 FireRed-OpenStoryline）
- [ ] HTML 模板渲染系统（参考 Pixelle-Video templates/）

## 贡献

欢迎提交 Issue 和 PR：

- Bug 报告 / 功能建议：[提 Issue](https://github.com/tepeiya/autotalk-studio/issues/new/choose)
- 代码贡献：fork → 分支 → PR，CI 通过即可合并
- 新增 Provider：参考 [Provider 扩展](#provider-扩展)，无需改动其他代码

贡献者请遵守 [MIT License](LICENSE)，提交即视为同意以同样协议开源。

## 相关项目

本系统借鉴了以下优秀开源项目，特此致谢：

- [Pixelle-Video](https://github.com/AIDC-Ai/Pixelle-Video) - ComfyUI 模块化架构 + 数字人口播
- [LuoGen-agent](https://github.com/LuoGen-AI/LuoGen-agent) - 商业级批量生产 + 多平台发布
- [FireRed-OpenStoryline](https://github.com/FireRedTeam/FireRed-OpenStoryline) - 对话式剪辑 + ASR 粗剪
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) - 主题 → 成片全自动化
- [Linly-Dubbing](https://github.com/Kedreamix/Linly-Dubbing) - 多语言配音 + 口型同步
- [AigcPanel](https://github.com/modstart-lib/aigcpanel) - 桌面端数字人系统
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) / [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) / [IndexTTS](https://github.com/index-tts/index-tts) - 声音克隆
- [MuseTalk](https://github.com/TMElyralab/MuseTalk) / [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) - 口型同步

## License

[MIT](LICENSE) © 2026 tepeiya

# AutoTalk Studio - 架构设计

> 一个把 Pixelle-Video / LuoGen-agent / FireRed-OpenStoryline / MoneyPrinterTurbo / Linly-Dubbing / AigcPanel / 元界AI 的优点集成到一起的「数字人口播视频自动生产系统」。

## 1. 设计目标

| 能力 | 来源借鉴 | 本系统交付 |
|---|---|---|
| AI 自动生成台词 | Pixelle-Video / MoneyPrinterTurbo | LLM Provider 抽象，支持 OpenAI / Qwen / Ollama |
| 声音克隆 TTS | GPT-SoVITS / CosyVoice / IndexTTS / 元界AI | TTS Provider 抽象，零样本 3s 克隆 |
| 数字人口播合成 | MuseTalk / Wav2Lip / HeyGem / AigcPanel | Avatar Provider 抽象，口型驱动 |
| 背景与音乐自动切换 | Pixelle-Video / MoneyPrinterTurbo | Media Provider，分镜级 BGM + 背景图/视频 |
| 批量任务调度 | LuoGen-agent / MoneyPrinterTurbo | TaskManager + 优先级队列 + 并发 |
| 多平台发布 | LuoGen-agent / 元界AI | Publisher 抽象（抖音/B站/快手），后续扩展 |
| 模块化可替换 | Pixelle-Video ComfyUI 架构 | 所有能力抽象为 Provider，配置化切换 |
| 桌面/服务双形态 | AigcPanel | FastAPI 后端 + Vue3 前端，可独立部署 |

## 2. 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│                       Vue3 + Vite 前端                       │
│  Dashboard / ScriptStudio / VoiceLab / AvatarStudio / ...   │
└───────────────────────────────┬──────────────────────────────┘
                                │ HTTP / SSE
┌───────────────────────────────▼──────────────────────────────┐
│                     FastAPI 应用层 (api/)                     │
│   projects / tasks / voices / avatars / media / publishers   │
└───────────────────────────────┬──────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────┐
│                 编排层 (core/pipeline.py)                     │
│  ScriptService → VoiceService → AvatarService → MediaService │
│                          → VideoService                      │
└───────────────────────────────┬──────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────┐
│            Provider 抽象层 (providers/base.py)               │
│  ┌─────┐ ┌─────┐ ┌────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ LLM │ │ TTS │ │ Avatar │ │  Media   │ │  Publisher    │  │
│  └──┬──┘ └──┬──┘ └───┬────┘ └────┬─────┘ └───────┬───────┘  │
│     │       │        │           │               │          │
│  OpenAI  Edge-TTS  MuseTalk    BGM库           抖音/B站       │
│  Ollama  CosyVoice Wav2Lip     背景模板         快手          │
│  Qwen    GPT-SoVITS HeyGem                                  │
│          IndexTTS                                            │
└───────────────────────────────┬──────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────┐
│         存储层 (core/storage.py + storage/)                   │
│   voices/  avatars/  bgm/  backgrounds/  videos/  tasks/      │
└──────────────────────────────────────────────────────────────┘
```

## 3. 目录结构

```
/workspace
├── PLAN.md                              # 本文件
├── README.md
├── docker-compose.yml
├── config/
│   ├── config.example.yaml              # 主配置
│   └── prompts/                         # LLM Prompt 模板
│       ├── script_generation.txt
│       └── shot_split.txt
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                      # FastAPI 入口
│   │   ├── config.py                    # Pydantic Settings
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routes/
│   │   │       ├── projects.py
│   │   │       ├── tasks.py
│   │   │       ├── voices.py
│   │   │       ├── avatars.py
│   │   │       ├── media.py
│   │   │       └── publishers.py
│   │   ├── core/
│   │   │   ├── schemas.py               # 所有 Pydantic 模型
│   │   │   ├── pipeline.py              # 编排
│   │   │   ├── task_manager.py          # 批量调度
│   │   │   └── storage.py               # 文件存储抽象
│   │   ├── providers/
│   │   │   ├── base.py                  # 抽象基类
│   │   │   ├── llm/
│   │   │   │   ├── base.py
│   │   │   │   ├── openai_provider.py
│   │   │   │   ├── ollama_provider.py
│   │   │   │   └── qwen_provider.py
│   │   │   ├── tts/
│   │   │   │   ├── base.py
│   │   │   │   ├── edge_tts_provider.py
│   │   │   │   ├── cosyvoice_provider.py
│   │   │   │   ├── gpt_sovits_provider.py
│   │   │   │   └── index_tts_provider.py
│   │   │   ├── avatar/
│   │   │   │   ├── base.py
│   │   │   │   ├── musetalk_provider.py
│   │   │   │   ├── wav2lip_provider.py
│   │   │   │   └── heygem_provider.py
│   │   │   ├── media/
│   │   │   │   ├── bgm_provider.py
│   │   │   │   └── background_provider.py
│   │   │   └── publisher/
│   │   │       ├── base.py
│   │   │       └── dummy_publisher.py
│   │   ├── services/
│   │   │   ├── script_service.py
│   │   │   ├── voice_service.py
│   │   │   ├── avatar_service.py
│   │   │   ├── media_service.py
│   │   │   └── video_service.py
│   │   └── utils/
│   │       ├── ffmpeg_utils.py
│   │       └── file_utils.py
│   └── tests/
│       └── test_pipeline.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/index.ts
│       ├── api/client.ts
│       ├── stores/{project,task}.ts
│       ├── views/{Dashboard,ScriptStudio,VoiceLab,AvatarStudio,MediaLibrary,BatchTasks,Settings}.vue
│       └── components/layout/Sidebar.vue
└── storage/                            # 运行时生成（gitignored）
```

## 4. 核心抽象：Provider 模式

所有外部能力（LLM/TTS/Avatar/Media/Publisher）实现统一的 `Provider` 接口：

```python
class BaseProvider(ABC):
    name: str
    type: str  # llm / tts / avatar / media / publisher
    requires_gpu: bool

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    def get_config_schema(self) -> dict: ...
```

每个具体 Provider（如 `CosyVoiceProvider`）继承抽象类，在 `app/config.py` 中通过 `provider_registry` 装配，运行时根据项目配置切换。

## 5. 数据流

```
用户创建 Project (topic="为什么要养成阅读习惯")
    │
    ▼
[ScriptService] LLM 生成文案 → 拆分为 N 个分镜
    │
    ▼
[VoiceService] 每分镜调用 TTS 克隆音色 → N 段音频
    │ (并行)
[MediaService] 每分镜随机/指定背景图 + BGM
    │
    ▼
[AvatarService] 每分镜用克隆音色驱动数字人 → N 段口播视频
    │
    ▼
[VideoService] ffmpeg 合成 → 最终 MP4
    │
    ▼
[Publisher] 可选发布到多平台
```

## 6. 任务调度

- `TaskManager` 维护优先级队列
- 每个 Project 是一个 Task，内含子任务（分镜级）
- 支持并发：同一 Project 内分镜并行，多 Project 串行/限并发
- 状态：`pending / running / success / failed / cancelled`
- 进度通过 SSE 推送到前端

## 7. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 后端框架 | FastAPI | 异步、自动 OpenAPI、生态好 |
| 配置 | Pydantic Settings + YAML | 类型安全 + 可读 |
| 任务队列 | asyncio + 内存队列（MVP），后期可换 Celery/RQ | 渐进 |
| 前端 | Vue3 + Vite + Pinia + Element Plus | 上手快、组件全 |
| 视频处理 | ffmpeg-python | 业界标准 |
| 异步 LLM | openai SDK（兼容 OpenAI/Ollama/Qwen） | 一套 SDK 通吃 |
| 容器化 | Docker Compose | 一键启动 |

## 8. MVP 范围

本期交付：
- ✅ 完整架构 + 框架代码（所有 Provider 抽象 + 至少 1 个具体实现）
- ✅ LLM：OpenAI + Ollama
- ✅ TTS：Edge-TTS（默认可用，无需 GPU） + CosyVoice / GPT-SoVITS 占位接入
- ✅ Avatar：MuseTalk / Wav2Lip 抽象 + 占位实现
- ✅ Media：本地 BGM 库 + 背景模板
- ✅ Pipeline 编排 + 批量任务
- ✅ FastAPI 路由 + SSE 进度
- ✅ Vue3 前端骨架 + 主要页面

后续扩展：
- ComfyUI 工作流接入（参考 Pixelle-Video）
- 真实多平台发布 SDK 接入
- 分布式任务队列（Celery + Redis）
- ASR 粗剪 / 转场生成（参考 FireRed-OpenStoryline）

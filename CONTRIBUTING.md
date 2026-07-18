# 贡献指南

感谢你对 AutoTalk Studio 的关注！欢迎提交 Issue、PR 或新增 Provider。

## 开发环境

```bash
# 后端
cd backend
pip install -e ".[dev]"
pytest tests/ -v
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## 贡献流程

1. Fork 仓库并克隆
2. 新建分支：`git checkout -b feat/your-feature`
3. 提交改动，遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：
   - `feat: 新增 XX Provider`
   - `fix: 修复 pipeline 中音频合成的 bug`
   - `docs: 更新 README`
   - `refactor: 重构 task_manager`
4. 推送分支到自己的 fork
5. 发起 PR 到 `main`，CI 通过即可合并

## Commit 规范

| 类型 | 说明 |
|---|---|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档改动 |
| refactor | 不影响功能的重构 |
| perf | 性能优化 |
| test | 增加测试 |
| chore | 构建 / 依赖 / 配置 |

## 新增 Provider

新增 Provider 是最常见的贡献方式：

```python
# backend/app/providers/tts/my_tts_provider.py
from ..base import registry
from .base import BaseTTSProvider

@registry.register
class MyTTSProvider(BaseTTSProvider):
    name = "my_tts"

    async def synthesize(self, text, voice_id, output_path, speed=1.0, pitch=0.0):
        # 实现合成逻辑
        return output_path
```

无需改动其他文件，前端 `/api/providers` 会自动列出。

## 测试要求

- 新功能请补一个最小测试到 `backend/tests/`
- Provider 实现请确保 `health_check()` 工作
- 不要破坏现有 `pytest tests/ -v` 的通过

## 代码风格

- Python: ruff（line-length=100）
- TypeScript: 2 空格缩进
- 注释和文档用中文（与现有代码一致）

## 行为准则

- 友善、尊重、对事不对人
- 欢迎新手贡献
- 拒绝任何形式的骚扰

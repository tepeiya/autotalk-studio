<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  providers as providersApi,
  settings as settingsApi,
  type ProviderInfo,
  type SettingsSnapshot,
} from '@/api/client'

// ──────────────────────────────────────────────────────────────────
// 状态
// ──────────────────────────────────────────────────────────────────

const STORAGE_KEY = 'autotalk.defaultProviders'

const loading = ref(false)
const saving = ref(false)
const snapshot = ref<SettingsSnapshot | null>(null)
const draft = reactive<Record<string, any>>({})

// 每个 provider 类型的候选列表（来自 /api/providers）
const providerGroups = ref<Record<string, ProviderInfo[]>>({})

// 浏览器本地的默认 provider 偏好（和旧版兼容，优先级低于后端配置）
const localDefaults = reactive<Record<string, string>>(loadLocalDefaults())

// 活动 Tab
const activeTab = ref<
  'general' | 'llm' | 'tts' | 'avatar' | 'media' | 'pipeline' | 'publisher' | 'providers'
>('llm')

// ──────────────────────────────────────────────────────────────────
// 字段定义（key / label / type / 可选 options）
// ──────────────────────────────────────────────────────────────────

type FieldType = 'text' | 'password' | 'number' | 'switch' | 'select'

interface FieldDef {
  key: string
  label: string
  type: FieldType
  placeholder?: string
  hint?: string
  options?: Array<{ label: string; value: string }>
  section: string // 对应 settings section（如 llm / tts / '' 表示根）
  min?: number
  max?: number
  step?: number
}

function providerOptions(type: string): Array<{ label: string; value: string }> {
  return [
    { label: '— 系统默认 —', value: '' },
    ...(providerGroups.value[type] || []).map((p) => ({
      label: p.name + (p.available ? '' : ' (unavailable)'),
      value: p.name,
    })),
  ]
}

const generalFields: FieldDef[] = [
  { section: '', key: 'host', label: '服务监听 IP', type: 'text', placeholder: '0.0.0.0' },
  { section: '', key: 'port', label: '服务端口', type: 'number', min: 1, max: 65535 },
  { section: '', key: 'cors_origins', label: '允许的跨域来源（逗号分隔）', type: 'text',
    hint: '例：http://localhost:5173,https://your.domain.com' },
  { section: '', key: 'storage_root', label: '存储根目录', type: 'text',
    hint: '视频/音频/图片等产物存放目录，建议挂独立盘' },
]

const llmFields: FieldDef[] = [
  { section: 'llm', key: 'default_provider', label: '默认 LLM Provider', type: 'select' },
  { section: 'llm', key: 'openai_api_key', label: 'OpenAI API Key', type: 'password',
    hint: '以 sk- 开头。任意兼容 OpenAI 协议的 Key 都行。' },
  { section: 'llm', key: 'openai_base_url', label: 'OpenAI Base URL', type: 'text',
    placeholder: 'https://api.openai.com/v1' },
  { section: 'llm', key: 'openai_model', label: 'OpenAI Model', type: 'text',
    placeholder: 'gpt-4o-mini' },
  { section: 'llm', key: 'qwen_api_key', label: '通义千问 (Qwen) API Key', type: 'password',
    hint: '从 dashscope.aliyuncs.com 获取。' },
  { section: 'llm', key: 'qwen_base_url', label: '通义千问 Base URL', type: 'text',
    placeholder: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { section: 'llm', key: 'qwen_model', label: '通义千问 Model', type: 'text',
    placeholder: 'qwen-max / qwen-plus' },
  { section: 'llm', key: 'ollama_base_url', label: 'Ollama Base URL', type: 'text',
    placeholder: 'http://127.0.0.1:11434/v1' },
  { section: 'llm', key: 'ollama_model', label: 'Ollama Model', type: 'text',
    placeholder: 'qwen2.5:7b' },
]

const ttsFields: FieldDef[] = [
  { section: 'tts', key: 'default_provider', label: '默认 TTS Provider', type: 'select' },
  { section: 'tts', key: 'edge_voice', label: 'Edge-TTS 发音人', type: 'text',
    hint: '例：zh-CN-XiaoxiaoNeural（中文女） / zh-CN-YunxiNeural（中文男）' },
  { section: 'tts', key: 'cosyvoice_base_url', label: 'CosyVoice 服务地址', type: 'text',
    placeholder: 'http://127.0.0.1:9880' },
  { section: 'tts', key: 'gptsovits_base_url', label: 'GPT-SoVITS 服务地址', type: 'text',
    placeholder: 'http://127.0.0.1:9880' },
  { section: 'tts', key: 'indextts_base_url', label: 'IndexTTS 服务地址', type: 'text',
    placeholder: 'http://127.0.0.1:8000' },
]

const avatarFields: FieldDef[] = [
  { section: 'avatar', key: 'default_provider', label: '默认数字人 Provider', type: 'select' },
  { section: 'avatar', key: 'musetalk_base_url', label: 'MuseTalk 服务地址', type: 'text',
    placeholder: 'http://127.0.0.1:8080',
    hint: '高质量对口型，推荐。需要 GPU 部署。' },
  { section: 'avatar', key: 'wav2lip_base_url', label: 'Wav2Lip 服务地址', type: 'text',
    placeholder: 'http://127.0.0.1:8081' },
  { section: 'avatar', key: 'heygem_base_url', label: 'HeyGem 服务地址', type: 'text',
    placeholder: 'http://127.0.0.1:8082' },
]

const mediaFields: FieldDef[] = [
  { section: 'media', key: 'bgm_dir', label: 'BGM 目录', type: 'text',
    hint: '前端 Media Library 页也能上传。' },
  { section: 'media', key: 'background_dir', label: '背景图目录', type: 'text' },
  { section: 'media', key: 'default_bgm_mode', label: '默认 BGM 模式', type: 'select',
    options: [
      { label: '随机（推荐）', value: 'random' },
      { label: '指定', value: 'specified' },
      { label: '无 BGM', value: 'none' },
    ] },
  { section: 'media', key: 'default_bg_mode', label: '默认背景模式', type: 'select',
    options: [
      { label: '模板', value: 'template' },
      { label: '随机', value: 'random' },
      { label: '指定', value: 'specified' },
    ] },
]

const pipelineFields: FieldDef[] = [
  { section: 'pipeline', key: 'max_concurrent_shots', label: '分镜最大并发', type: 'number',
    min: 1, max: 32, step: 1,
    hint: '并行越高越快，但更占显存/内存。' },
  { section: 'pipeline', key: 'shot_parallel', label: '开启分镜并行合成', type: 'switch' },
  { section: 'pipeline', key: 'output_resolution', label: '输出分辨率', type: 'select',
    options: [
      { label: '竖屏 1080×1920 (9:16 小红书/抖音)', value: '1080x1920' },
      { label: '竖屏 720×1280 (9:16)', value: '720x1280' },
      { label: '横屏 1920×1080 (16:9)', value: '1920x1080' },
      { label: '横屏 1280×720 (16:9)', value: '1280x720' },
      { label: '方屏 1080×1080 (1:1)', value: '1080x1080' },
    ] },
]

const publisherFields: FieldDef[] = [
  { section: 'publisher', key: 'default_provider', label: '默认 Publisher', type: 'select' },
]

const tabFields: Record<string, FieldDef[]> = {
  general: generalFields,
  llm: llmFields,
  tts: ttsFields,
  avatar: avatarFields,
  media: mediaFields,
  pipeline: pipelineFields,
  publisher: publisherFields,
}

// Provider 组标签（用于 Default Providers 页）
const providerGroupLabels: Record<string, string> = {
  llm: 'LLM (Script / 翻译润色)',
  tts: 'TTS (语音合成)',
  avatar: 'Avatar (数字人口型)',
  media: 'Media (BGM / 背景)',
  publisher: 'Publisher (发布平台)',
  collector: 'Collector (Reddit 采集)',
  translator: 'Translator (Reddit 翻译)',
  image: 'Image (Reddit 配图)',
  note: 'Note (Reddit 笔记生成)',
}

const providerGroupKeys = computed(() => Object.keys(providerGroups.value))

// ──────────────────────────────────────────────────────────────────
// 方法
// ──────────────────────────────────────────────────────────────────

function loadLocalDefaults(): Record<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveLocalDefaults() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(localDefaults))
}

function readFromDraft(field: FieldDef): any {
  const section = field.section
  const obj = section ? (draft[section] || (draft[section] = {})) : draft
  return obj[field.key]
}

function writeToDraft(field: FieldDef, value: any) {
  const section = field.section
  const obj = section ? (draft[section] || (draft[section] = {})) : draft
  obj[field.key] = value
}

async function loadAll() {
  loading.value = true
  try {
    const [snap, grouped] = await Promise.all([
      settingsApi.fetchSnapshot(),
      providersApi.listProviders(),
    ])
    snapshot.value = snap
    // 拷贝到 draft（用户可编辑副本）
    for (const [k, v] of Object.entries(snap)) {
      draft[k] = typeof v === 'object' && v != null ? { ...(v as object) } : v
    }
    // provider 分组
    const grp: Record<string, ProviderInfo[]> = {}
    for (const p of grouped) {
      if (!grp[p.type]) grp[p.type] = []
      grp[p.type].push(p)
    }
    providerGroups.value = grp
  } catch (e: any) {
    ElMessage.error(`加载配置失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

/** 比较 draft 与 snapshot，生成 patch（只传变化的部分） */
function buildPatch(): Record<string, any> {
  if (!snapshot.value) return {}
  const patch: Record<string, any> = {}
  for (const sectionKey of [
    '', 'llm', 'tts', 'avatar', 'media', 'publisher', 'pipeline',
  ] as const) {
    const base = sectionKey
      ? snapshot.value[sectionKey as keyof SettingsSnapshot]
      : snapshot.value
    const d = sectionKey ? draft[sectionKey] : draft
    if (typeof base !== 'object' || !base || typeof d !== 'object' || !d) continue
    for (const [k, v] of Object.entries(d)) {
      const baseVal = (base as Record<string, any>)[k]
      if (JSON.stringify(baseVal) === JSON.stringify(v)) continue
      const target = sectionKey ? (patch[sectionKey] || (patch[sectionKey] = {})) : patch
      target[k] = v
    }
  }
  // 特殊：host/port/cors_origins/storage_root 属于根
  return patch
}

async function onSave() {
  if (!snapshot.value) {
    ElMessage.warning('配置尚未加载完成')
    return
  }
  const patch = buildPatch()
  // 空 patch 也给提示
  const empty =
    Object.keys(patch).filter(
      (k) => typeof patch[k] !== 'object' || Object.keys(patch[k]).length > 0
    ).length === 0
  if (empty) {
    ElMessage.info('没有检测到任何改动')
    return
  }
  try {
    saving.value = true
    await ElMessageBox.confirm(
      '修改会立即持久化到 config/config.yaml，下次请求立刻生效（host/port 需重启后端）。确定保存？',
      '保存系统配置',
      { type: 'warning' }
    )
  } catch {
    saving.value = false
    return
  }
  try {
    const updated = await settingsApi.updateSnapshot(patch as any)
    snapshot.value = updated
    ElMessage.success('配置已保存 ✅')
  } catch (e: any) {
    ElMessage.error(`保存失败: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function onResetPage() {
  // 仅还原当前 draft 到快照（不碰磁盘）
  if (!snapshot.value) return
  try {
    await ElMessageBox.confirm('放弃当前页面所有未保存的修改？', '重置表单', {
      type: 'warning',
    })
  } catch {
    return
  }
  for (const [k, v] of Object.entries(snapshot.value)) {
    draft[k] = typeof v === 'object' && v != null ? { ...(v as object) } : v
  }
  ElMessage.info('已还原为服务器当前配置')
}

function onSaveLocalProviders() {
  saveLocalDefaults()
  ElMessage.success('默认 Provider 已保存在当前浏览器 (localStorage)')
}

function onResetLocalProviders() {
  for (const k of Object.keys(localDefaults)) localDefaults[k] = ''
  saveLocalDefaults()
  ElMessage.info('已清空本地默认 Provider')
}

// 给 Field 选 type 时，若是 select 且没显式 options，就用 provider groups
function effectiveOptions(f: FieldDef): Array<{ label: string; value: string }> {
  if (f.type !== 'select') return []
  if (f.options) return f.options
  return providerOptions(f.section)
}

onMounted(loadAll)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">系统设置</h2>

    <el-alert
      v-if="snapshot"
      type="success"
      show-icon
      :closable="false"
      class="mb-16"
    >
      <template #title>
        配置已从服务器加载（持久化路径：
        <code class="mono">{{ snapshot.yaml_path }}</code>
        ）
      </template>
      环境变量（如 <code>LLM__OPENAI_API_KEY</code>）优先级高于本页面，若你发现某字段改了不生效，请检查是否被环境变量覆盖。
    </el-alert>

    <el-tabs v-model="activeTab" type="border-card" v-loading="loading">
      <!-- 🔐 LLM -->
      <el-tab-pane label="🤖 大模型 LLM" name="llm">
        <el-form label-width="200px" class="settings-form">
          <template v-for="f in tabFields.llm" :key="f.key">
            <el-form-item :label="f.label">
              <el-input
                v-if="f.type === 'text'"
                :model-value="readFromDraft(f)"
                :placeholder="f.placeholder"
                clearable
                style="width: 480px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              />
              <el-input
                v-else-if="f.type === 'password'"
                :model-value="readFromDraft(f)"
                :placeholder="f.placeholder"
                type="password"
                show-password
                clearable
                style="width: 480px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              />
              <el-select
                v-else-if="f.type === 'select'"
                :model-value="readFromDraft(f)"
                clearable
                placeholder="选择"
                style="width: 320px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v ?? '')"
              >
                <el-option
                  v-for="o in effectiveOptions(f)"
                  :key="o.value"
                  :label="o.label"
                  :value="o.value"
                />
              </el-select>
              <div v-if="f.hint" class="hint">{{ f.hint }}</div>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- 🔊 TTS -->
      <el-tab-pane label="🔊 语音合成 TTS" name="tts">
        <el-form label-width="200px" class="settings-form">
          <template v-for="f in tabFields.tts" :key="f.key">
            <el-form-item :label="f.label">
              <el-input
                v-if="f.type === 'text'"
                :model-value="readFromDraft(f)"
                :placeholder="f.placeholder"
                clearable
                style="width: 480px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              />
              <el-select
                v-else-if="f.type === 'select'"
                :model-value="readFromDraft(f)"
                clearable
                style="width: 320px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v ?? '')"
              >
                <el-option
                  v-for="o in effectiveOptions(f)"
                  :key="o.value"
                  :label="o.label"
                  :value="o.value"
                />
              </el-select>
              <div v-if="f.hint" class="hint">{{ f.hint }}</div>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- 🧑 Avatar -->
      <el-tab-pane label="🧑 数字人口播 Avatar" name="avatar">
        <el-form label-width="200px" class="settings-form">
          <template v-for="f in tabFields.avatar" :key="f.key">
            <el-form-item :label="f.label">
              <el-input
                v-if="f.type === 'text'"
                :model-value="readFromDraft(f)"
                :placeholder="f.placeholder"
                clearable
                style="width: 480px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              />
              <el-select
                v-else-if="f.type === 'select'"
                :model-value="readFromDraft(f)"
                clearable
                style="width: 320px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v ?? '')"
              >
                <el-option
                  v-for="o in effectiveOptions(f)"
                  :key="o.value"
                  :label="o.label"
                  :value="o.value"
                />
              </el-select>
              <div v-if="f.hint" class="hint">{{ f.hint }}</div>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- 🎬 Pipeline -->
      <el-tab-pane label="🎬 流水线 Pipeline" name="pipeline">
        <el-form label-width="200px" class="settings-form">
          <template v-for="f in tabFields.pipeline" :key="f.key">
            <el-form-item :label="f.label">
              <el-input-number
                v-if="f.type === 'number'"
                :model-value="Number(readFromDraft(f) || 0)"
                :min="f.min"
                :max="f.max"
                :step="f.step ?? 1"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, Number(v))"
              />
              <el-switch
                v-else-if="f.type === 'switch'"
                :model-value="!!readFromDraft(f)"
                @update:model-value="(v) => writeToDraft(f, v)"
              />
              <el-select
                v-else-if="f.type === 'select'"
                :model-value="readFromDraft(f)"
                style="width: 420px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              >
                <el-option
                  v-for="o in effectiveOptions(f)"
                  :key="o.value"
                  :label="o.label"
                  :value="o.value"
                />
              </el-select>
              <div v-if="f.hint" class="hint">{{ f.hint }}</div>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- 🎵 Media -->
      <el-tab-pane label="🎵 素材 Media" name="media">
        <el-form label-width="200px" class="settings-form">
          <template v-for="f in tabFields.media" :key="f.key">
            <el-form-item :label="f.label">
              <el-input
                v-if="f.type === 'text'"
                :model-value="readFromDraft(f)"
                clearable
                style="width: 480px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              />
              <el-select
                v-else-if="f.type === 'select'"
                :model-value="readFromDraft(f)"
                style="width: 320px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              >
                <el-option
                  v-for="o in effectiveOptions(f)"
                  :key="o.value"
                  :label="o.label"
                  :value="o.value"
                />
              </el-select>
              <div v-if="f.hint" class="hint">{{ f.hint }}</div>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- 📤 Publisher -->
      <el-tab-pane label="📤 发布 Publisher" name="publisher">
        <el-form label-width="200px" class="settings-form">
          <template v-for="f in tabFields.publisher" :key="f.key">
            <el-form-item :label="f.label">
              <el-select
                v-if="f.type === 'select'"
                :model-value="readFromDraft(f)"
                clearable
                style="width: 320px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v ?? '')"
              >
                <el-option
                  v-for="o in effectiveOptions(f)"
                  :key="o.value"
                  :label="o.label"
                  :value="o.value"
                />
              </el-select>
              <div v-if="f.hint" class="hint">{{ f.hint }}</div>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- 🌍 通用 -->
      <el-tab-pane label="🌍 通用 General" name="general">
        <el-form label-width="200px" class="settings-form">
          <template v-for="f in tabFields.general" :key="f.key">
            <el-form-item :label="f.label">
              <el-input-number
                v-if="f.type === 'number'"
                :model-value="Number(readFromDraft(f) || 0)"
                :min="f.min"
                :max="f.max"
                :step="1"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, Number(v))"
              />
              <el-input
                v-else
                :model-value="readFromDraft(f)"
                :placeholder="f.placeholder"
                clearable
                style="width: 480px"
                class="mobile-fullwidth"
                @update:model-value="(v) => writeToDraft(f, v)"
              />
              <div v-if="f.hint" class="hint">{{ f.hint }}</div>
            </el-form-item>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- 🛠 Default Providers（本地 localStorage，兼容历史） -->
      <el-tab-pane label="🛠 默认 Providers (本地)" name="providers">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="这些选择仅保存在当前浏览器（localStorage），不影响后端默认。"
          class="mb-16"
        />

        <el-empty v-if="providerGroupKeys.length === 0" description="暂无 Provider 列表" />

        <el-form v-else label-width="240px">
          <el-form-item
            v-for="key in providerGroupKeys"
            :key="key"
            :label="providerGroupLabels[key] || key"
          >
            <el-select
              v-model="localDefaults[key]"
              placeholder="系统默认（后端 default_provider）"
              clearable
              style="width: 320px"
              class="mobile-fullwidth"
            >
              <el-option
                v-for="p in providerGroups[key]"
                :key="p.name"
                :label="p.name + (p.available ? '' : '  (unavailable)')"
                :value="p.name"
                :disabled="!p.available"
              />
            </el-select>
            <span class="hint">
              共 {{ providerGroups[key].length }} 个 provider
            </span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="onSaveLocalProviders">保存本地偏好</el-button>
            <el-button @click="onResetLocalProviders">清空</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <!-- 底部操作栏 -->
    <div class="footer-actions">
      <el-button type="primary" :loading="saving" size="large" @click="onSave">
        💾 保存所有配置到服务器
      </el-button>
      <el-button size="large" @click="onResetPage" :disabled="loading">
        ↩ 放弃当前修改
      </el-button>
      <el-button size="large" plain @click="loadAll" :disabled="loading">
        🔄 从服务器重新加载
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.mono {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: #606266;
}

.footer-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px dashed #ebeef5;
}

.settings-form {
  max-width: 900px;
}

/* ========== 平板 ≤1024px ========== */
@media (max-width: 1024px) {
  :deep(.el-tabs--border-card > .el-tabs__content) {
    padding: 14px;
  }
  :deep(.el-tabs__header) {
    margin: 0;
  }
}

/* ========== 手机 ≤768px ========== */
@media (max-width: 768px) {
  :deep(.el-tabs--border-card > .el-tabs__content) {
    padding: 12px;
  }

  :deep(.el-tabs__nav) {
    flex-wrap: nowrap;
    overflow-x: auto;
  }
  :deep(.el-tabs__nav .el-tabs__item) {
    white-space: nowrap;
    flex-shrink: 0;
  }

  .settings-form :deep(.el-form-item__label) {
    font-size: 12px;
    width: 140px !important;
    padding-right: 6px !important;
  }

  .settings-form :deep(.el-form-item) {
    margin-bottom: 14px;
  }

  .hint {
    display: block;
    margin-left: 0;
    margin-top: 4px;
  }

  .footer-actions {
    gap: 8px;
  }
  .footer-actions > .el-button {
    flex: 1;
    min-width: 45%;
  }
}

/* ========== 小屏手机 ≤480px ========== */
@media (max-width: 480px) {
  .settings-form :deep(.el-form-item__label) {
    font-size: 11px;
    width: 120px !important;
  }
}
</style>

<script setup lang="ts">
import { reactive, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import {
  providers as providersApi,
  projects as projectsApi,
  type ProviderInfo,
  type ProjectCreatePayload,
  type PreflightResult,
  type CostEstimateResult,
} from '@/api/client'
import { useProjectStore } from '@/stores/project'

const router = useRouter()
const projectStore = useProjectStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const preflighting = ref(false)
const costing = ref(false)
const llmProviders = ref<ProviderInfo[]>([])
const ttsProviders = ref<ProviderInfo[]>([])

// collapse v-model 绑定的 ref（必须和模板在同一 script setup 作用域）
const preflightActive = ref<string[]>(['preflight'])
const costActive = ref<string[]>(['cost'])

const form = reactive<ProjectCreatePayload>({
  name: '',
  topic: '',
  style: 'informative',
  duration_sec: 60,
  language: 'zh',
  orientation: 'portrait',
  reference_text: '',
  llm_provider: '',
  tts_provider: '',
  auto_publish: false,
  publish_platforms: [],
  // 新增：预检 / 预览审批 / 费用确认 —— 默认全关，保留原行为
  enable_preview_approval: false,
  preview_duration_sec: 15,
  require_asset_preflight: false,
  require_cost_confirmation: false,
})

const lastPreflight = ref<PreflightResult | null>(null)
const lastCost = ref<CostEstimateResult | null>(null)

// 表单 payload 归一化（和旧 onSubmit 逻辑一致），供预检/创建/费用估算复用
function buildPayload(): ProjectCreatePayload {
  return {
    ...form,
    name: form.name?.trim() || form.topic.trim(),
    topic: form.topic.trim(),
    llm_provider: form.llm_provider || null,
    tts_provider: form.tts_provider || null,
    reference_text: form.reference_text || null,
    publish_platforms: form.auto_publish ? form.publish_platforms : [],
  }
}

const rules: FormRules = {
  topic: [{ required: true, message: 'Topic is required', trigger: 'blur' }],
  style: [{ required: true, message: 'Style is required', trigger: 'change' }],
  language: [{ required: true, message: 'Language is required', trigger: 'change' }],
  duration_sec: [{ required: true, message: 'Duration is required', trigger: 'blur' }],
}

const styleOptions = [
  { label: 'Informative', value: 'informative' },
  { label: 'Humorous', value: 'humorous' },
  { label: 'Emotional', value: 'emotional' },
  { label: 'Sales', value: 'sales' },
]

const languageOptions = [
  { label: '中文', value: 'zh' },
  { label: 'English', value: 'en' },
  { label: '日本語', value: 'ja' },
  { label: '한국어', value: 'ko' },
]

const orientationOptions = [
  { label: 'Portrait 9:16', value: 'portrait' },
  { label: 'Landscape 16:9', value: 'landscape' },
  { label: 'Square 1:1', value: 'square' },
]

const platformOptions = [
  { label: '抖音 (Douyin)', value: 'douyin' },
  { label: 'B 站 (Bilibili)', value: 'bilibili' },
  { label: '快手 (Kuaishou)', value: 'kuaishou' },
  { label: '小红书 (Xiaohongshu)', value: 'xiaohongshu' },
  { label: 'YouTube', value: 'youtube' },
]

async function loadProviders() {
  try {
    const list = await providersApi.listProviders()
    llmProviders.value = list.filter((p) => p.type === 'llm')
    ttsProviders.value = list.filter((p) => p.type === 'tts')
  } catch (e: any) {
    ElMessage.warning(`Failed to load providers: ${e.message}`)
  }
}

// ──────────── 1. 预检（借鉴 Rachel Skill preflight_assets）────────────
async function onPreflight() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    preflighting.value = true
    try {
      const pf = await projectsApi.preflight(buildPayload())
      lastPreflight.value = pf
      if (!pf.passed) {
        ElMessage.warning(`${pf.summary}（预检未通过，但非强制模式下仍可运行）`)
      } else {
        ElMessage.success(pf.summary)
      }
    } catch (e: any) {
      ElMessage.error(`预检失败：${e.message}`)
    } finally {
      preflighting.value = false
    }
  })
}

// ──────────── 2. 费用估算（借鉴 Rachel Skill 付费前提示）────────────
async function onEstimateCost() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    costing.value = true
    try {
      const c = await projectsApi.estimateCost(buildPayload())
      lastCost.value = c
      ElMessage({
        type: c.total_cny < 0.5 ? 'success' : 'warning',
        message: c.summary,
        duration: 5000,
        showClose: true,
      })
    } catch (e: any) {
      ElMessage.error(`费用估算失败：${e.message}`)
    } finally {
      costing.value = false
    }
  })
}

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    const payload = buildPayload()

    // 预检强制模式（用户勾了 require_asset_preflight）：预检不过不给提交
    if (payload.require_asset_preflight) {
      try {
        const pf = lastPreflight.value || (await projectsApi.preflight(payload))
        lastPreflight.value = pf
        if (!pf.passed) {
          ElMessageBox.alert(
            `当前开启了【强制预检资产】，请先修复下方 ${pf.error_count} 个错误后再提交：\n` +
              pf.issues.filter((i) => i.level === 'error').map((i) => `• [${i.code}] ${i.message}`).join('\n'),
            '预检未通过',
            { type: 'warning', confirmButtonText: '好的' },
          )
          return
        }
      } catch (e: any) {
        ElMessage.error(`预检失败：${e.message}`)
        return
      }
    }

    // 费用确认强制模式：先弹费用确认框
    if (payload.require_cost_confirmation) {
      try {
        const c = lastCost.value || (await projectsApi.estimateCost(payload))
        lastCost.value = c
        if (c.total_cny > 0) {
          await ElMessageBox.confirm(
            `预估总花费约 ¥${c.total_cny.toFixed(3)}（${c.summary}），确认继续？\n\n` +
              c.items.map((i) => `• ${i.stage}(${i.provider})：¥${i.estimated_cost_cny.toFixed(4)} — ${i.note || ''}`).join('\n'),
            '费用确认',
            { confirmButtonText: '继续并创建', cancelButtonText: '取消', type: 'warning' },
          )
        }
      } catch (e: any) {
        if (e !== 'cancel') ElMessage.error(`费用确认失败：${e}`)
        return
      }
    }

    submitting.value = true
    try {
      // 使用新的 createProjectWithChecks（可走 preview_approval 流程，默认关则完全等价旧 create + submit）
      const project = await projectsApi.createProjectWithChecks(payload)
      ElMessage.success(`Project created: ${project.id}`)

      // 若启用了预览审批，则不直接去 tasks（因为还在 PENDING，等用户点预览）
      // 这里统一跳到 /tasks 详情，由 tasks 页面处理 preview/approve
      router.push({ path: '/tasks', query: { id: project.id } })
    } catch (e: any) {
      ElMessage.error(`Create failed: ${e.message}`)
    } finally {
      submitting.value = false
    }
  })
}

function onReset() {
  formRef.value?.resetFields()
  lastPreflight.value = null
  lastCost.value = null
}

onMounted(loadProviders)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">Script Studio</h2>

    <el-card shadow="never" class="section-card">
      <template #header>
        <span>Create a new video project</span>
      </template>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="140px"
        label-position="right"
      >
        <el-form-item label="Project Name" prop="name">
          <el-input
            v-model="form.name"
            placeholder="Optional - defaults to topic"
            clearable
          />
        </el-form-item>

        <el-form-item label="Topic" prop="topic">
          <el-input
            v-model="form.topic"
            type="textarea"
            :rows="2"
            placeholder="Video topic or keywords"
            clearable
          />
        </el-form-item>

        <el-form-item label="Style" prop="style">
          <el-select v-model="form.style" placeholder="Select style">
            <el-option
              v-for="opt in styleOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Duration (sec)" prop="duration_sec">
          <el-input-number
            v-model="form.duration_sec"
            :min="10"
            :max="600"
            :step="10"
          />
        </el-form-item>

        <el-form-item label="Language" prop="language">
          <el-select v-model="form.language" placeholder="Select language">
            <el-option
              v-for="opt in languageOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Orientation">
          <el-select v-model="form.orientation">
            <el-option
              v-for="opt in orientationOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="LLM Provider">
          <el-select
            v-model="form.llm_provider"
            placeholder="Use default"
            clearable
          >
            <el-option
              v-for="p in llmProviders"
              :key="p.name"
              :label="p.name"
              :value="p.name"
              :disabled="!p.available"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="TTS Provider">
          <el-select
            v-model="form.tts_provider"
            placeholder="Use default"
            clearable
          >
            <el-option
              v-for="p in ttsProviders"
              :key="p.name"
              :label="p.name"
              :value="p.name"
              :disabled="!p.available"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Reference Text">
          <el-input
            v-model="form.reference_text"
            type="textarea"
            :rows="4"
            placeholder="Optional reference text for few-shot imitation"
          />
        </el-form-item>

        <el-form-item label="Auto Publish">
          <el-switch v-model="form.auto_publish" />
          <span class="form-hint">开启后 pipeline 跑完自动发布到所选平台</span>
        </el-form-item>

        <el-form-item v-if="form.auto_publish" label="Publish Platforms">
          <el-select
            v-model="form.publish_platforms"
            multiple
            placeholder="选择要发布的平台"
            style="width: 100%"
          >
            <el-option
              v-for="opt in platformOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        {/* ================= 新增：预检 / 预览审批 / 费用确认（借鉴 Rachel Skill） ================= */}
        <el-divider content-position="left">🛡 流程控制（默认关闭，不影响原有行为）</el-divider>

        <el-alert
          title="三项功能默认关闭，全部勾选后即可获得 Rachel playbook 式严谨流程：资产预检 → 费用确认 → 15s 预览 → 人工审批 → 全量合成"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />

        <el-form-item label="强制资产预检">
          <el-switch v-model="form.require_asset_preflight" />
          <span class="form-hint">
            开启后，<b>提交前必须通过预检</b>（有 error 项无法提交）。
            建议搭配「预检按钮」使用。
          </span>
        </el-form-item>

        <el-form-item label="启用费用确认">
          <el-switch v-model="form.require_cost_confirmation" />
          <span class="form-hint">
            开启后，提交前弹出费用确认框（LLM/TTS/Avatar/Publish 分项估算）。
          </span>
        </el-form-item>

        <el-form-item label="启用预览-审批流">
          <el-switch v-model="form.enable_preview_approval" />
          <span class="form-hint">
            开启后，创建项目不会立刻全量跑，先等你点「生成 15s 预览」→ 审批通过 → 再全量合成。
          </span>
        </el-form-item>

        <el-form-item v-if="form.enable_preview_approval" label="预览时长 (秒)">
          <el-input-number
            v-model="form.preview_duration_sec"
            :min="5"
            :max="60"
            :step="5"
          />
          <span class="form-hint">建议 10-20 秒，预览成本大约是全量的 1/4~1/5。</span>
        </el-form-item>

        <el-form-item label="预检 / 估算">
          <div class="btn-row">
            <div class="btn-item">
              <el-button :loading="preflighting" type="success" @click="onPreflight">
                🔍 预检资产
              </el-button>
            </div>
            <div class="btn-item">
              <el-button :loading="costing" type="warning" @click="onEstimateCost">
                💰 估算费用
              </el-button>
            </div>
            <div class="btn-item">
              <el-button type="primary" :loading="submitting" @click="onSubmit">
                Create Project
              </el-button>
            </div>
            <div class="btn-item">
              <el-button @click="onReset">Reset</el-button>
            </div>
          </div>
        </el-form-item>

        {/* 预检报告 */}
        <el-collapse v-if="lastPreflight" v-model="preflightActive">
          <el-collapse-item title-class="preflight-title" name="preflight">
            <template #title>
              <span>
                🛡 预检报告：{{ lastPreflight.summary }}
                （错误 {{ lastPreflight.error_count }} / 警告 {{ lastPreflight.warning_count }} / 提示 {{ lastPreflight.info_count }}）
              </span>
            </template>
            <div v-for="issue in lastPreflight.issues" :key="issue.code" class="preflight-issue">
              <el-tag
                :type="{ error: 'danger', warning: 'warning', info: 'info' }[issue.level] as any"
                size="small"
                effect="light"
              >{{ issue.level.toUpperCase() }} / {{ issue.code }}</el-tag>
              <span class="preflight-msg">{{ issue.message }}</span>
              <el-tag v-if="issue.field" size="small" type="info">字段：{{ issue.field }}</el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>

        {/* 费用估算报告 */}
        <el-collapse v-if="lastCost" v-model="costActive">
          <el-collapse-item name="cost">
            <template #title>
              <span>💰 费用估算：{{ lastCost.summary }}（总 ¥{{ lastCost.total_cny.toFixed(3) }}，置信度 {{ lastCost.confidence }}）</span>
            </template>
            <el-table :data="lastCost.items" size="small" border stripe>
              <el-table-column prop="stage" label="阶段" width="90" />
              <el-table-column prop="provider" label="Provider" width="180" />
              <el-table-column label="用量">
                <template #default="{ row }">
                  {{ row.estimated_units.toFixed(2) }} {{ row.unit }}
                  <span class="dim"> @ ¥{{ row.unit_cost_cny.toFixed(6) }}/{{ row.unit }}</span>
                </template>
              </el-table-column>
              <el-table-column label="小计（¥）" width="110" align="right">
                <template #default="{ row }">
                  <b>{{ row.estimated_cost_cny.toFixed(4) }}</b>
                </template>
              </el-table-column>
              <el-table-column prop="note" label="备注" min-width="180" show-overflow-tooltip />
            </el-table>
          </el-collapse-item>
        </el-collapse>
      </el-form>
    </el-card>
  </div>
</template>

<script lang="ts">
export default {}
</script>

<style scoped>
.form-hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.btn-item { flex: 0 0 auto; }

.preflight-title { font-weight: 600; }
.preflight-issue {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 2px;
  border-bottom: 1px dashed #ebeef5;
}
.preflight-issue:last-child { border-bottom: none; }
.preflight-msg { flex: 1; font-size: 13px; color: #303133; }
.dim { color: #909399; font-size: 12px; }

/* ========== 平板 ≤1024px ========== */
@media (max-width: 1024px) {
  .section-card :deep(.el-card__body) {
    padding: 14px;
  }
}

/* ========== 手机 ≤768px ========== */
@media (max-width: 768px) {
  .section-card :deep(.el-card__body) {
    padding: 12px;
  }

  .section-card :deep(.el-form) {
    padding: 0;
  }

  .section-card :deep(.el-form-item) {
    margin-bottom: 14px;
  }

  .section-card :deep(.el-form-item__label) {
    font-size: 12px;
    width: 110px !important;
    padding-right: 6px !important;
  }

  .section-card :deep(.el-form-item__content) {
    min-width: 0;
  }

  .section-card :deep(.el-input),
  .section-card :deep(.el-select),
  .section-card :deep(.el-input-number),
  .section-card :deep(.el-textarea) {
    width: 100% !important;
  }

  .section-card :deep(.el-textarea__inner) {
    width: 100% !important;
  }

  .form-hint {
    display: block;
    margin-left: 0;
    margin-top: 4px;
  }

  .btn-row {
    flex-direction: column;
    gap: 8px;
  }
  .btn-item { width: 100%; }
  .btn-item .el-button { width: 100%; }

  .preflight-issue { flex-direction: column; align-items: flex-start; gap: 6px; }
}

/* ========== 小屏手机 ≤480px ========== */
@media (max-width: 480px) {
  .section-card :deep(.el-form-item__label) {
    font-size: 11px;
    width: 100px !important;
  }

  .section-card :deep(.el-card__body) {
    padding: 10px;
  }
}
</style>

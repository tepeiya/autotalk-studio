<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  providers as providersApi,
  type ProviderInfo,
  type ProjectCreatePayload,
} from '@/api/client'
import { useProjectStore } from '@/stores/project'

const router = useRouter()
const projectStore = useProjectStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const llmProviders = ref<ProviderInfo[]>([])
const ttsProviders = ref<ProviderInfo[]>([])

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
})

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

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const payload: ProjectCreatePayload = {
        ...form,
        name: form.name?.trim() || form.topic.trim(),
        topic: form.topic.trim(),
        llm_provider: form.llm_provider || null,
        tts_provider: form.tts_provider || null,
        reference_text: form.reference_text || null,
        publish_platforms: form.auto_publish ? form.publish_platforms : [],
      }
      const project = await projectStore.createProject(payload)
      ElMessage.success(`Project created: ${project.id}`)
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

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="onSubmit">
            Create Project
          </el-button>
          <el-button @click="onReset">Reset</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.form-hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>

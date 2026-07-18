<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  providers as providersApi,
  type ProviderInfo,
} from '@/api/client'

const STORAGE_KEY = 'autotalk.defaultProviders'

const providerGroups = ref<Record<string, ProviderInfo[]>>({})
const loading = ref(false)

const defaults = reactive<Record<string, string>>(loadDefaults())

const groupLabels: Record<string, string> = {
  llm: 'LLM (Script)',
  tts: 'TTS (Voice)',
  avatar: 'Avatar',
  media: 'Media',
  publisher: 'Publisher',
}

const groupKeys = computed(() => Object.keys(providerGroups.value))

function loadDefaults(): Record<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveDefaults() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(defaults))
}

async function loadProviders() {
  loading.value = true
  try {
    const list = await providersApi.listProviders()
    const grouped: Record<string, ProviderInfo[]> = {}
    for (const p of list) {
      if (!grouped[p.type]) grouped[p.type] = []
      grouped[p.type].push(p)
    }
    providerGroups.value = grouped
  } catch (e: any) {
    ElMessage.error(`Failed to load providers: ${e.message}`)
  } finally {
    loading.value = false
  }
}

function onSave() {
  saveDefaults()
  ElMessage.success('Default providers saved (browser only)')
}

function onReset() {
  for (const k of Object.keys(defaults)) defaults[k] = ''
  saveDefaults()
  ElMessage.info('Defaults cleared')
}

watch(defaults, () => {
  // keep in sync implicitly; explicit save on button
}, { deep: true })

onMounted(loadProviders)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">Settings</h2>

    <el-card class="section-card" shadow="never" v-loading="loading">
      <template #header>
        <div class="flex-between">
          <span>Default Providers</span>
          <el-button text @click="loadProviders">Refresh</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="These preferences are stored only in your browser (localStorage)."
        class="mb-16"
      />

      <el-empty v-if="groupKeys.length === 0" description="No providers available" />

      <el-form v-else label-width="180px">
        <el-form-item
          v-for="key in groupKeys"
          :key="key"
          :label="groupLabels[key] || key"
        >
          <el-select
            v-model="defaults[key]"
            placeholder="Use system default"
            clearable
            style="width: 320px"
          >
            <el-option
              v-for="p in providerGroups[key]"
              :key="p.name"
              :label="p.name"
              :value="p.name"
              :disabled="!p.available"
            />
          </el-select>
          <span class="hint">
            {{ providerGroups[key].length }} provider(s) registered
          </span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="onSave">Save</el-button>
          <el-button @click="onReset">Reset</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header><span>About</span></template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="Application">AutoTalk Studio</el-descriptions-item>
        <el-descriptions-item label="Backend">FastAPI @ http://localhost:8000</el-descriptions-item>
        <el-descriptions-item label="API Base">/api</el-descriptions-item>
        <el-descriptions-item label="Static">/static</el-descriptions-item>
        <el-descriptions-item label="Docs">http://localhost:8000/docs</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>

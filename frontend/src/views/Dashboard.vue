<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  providers as providersApi,
  projects as projectsApi,
  type ProviderInfo,
  type Project,
  type TaskStatus,
} from '@/api/client'

const router = useRouter()

const providerGroups = ref<Record<string, ProviderInfo[]>>({})
const recentProjects = ref<Project[]>([])
const loadingProviders = ref(false)
const loadingProjects = ref(false)

const groupKeys = computed(() => Object.keys(providerGroups.value))

const groupLabels: Record<string, string> = {
  llm: 'LLM (Script)',
  tts: 'TTS (Voice)',
  avatar: 'Avatar',
  media: 'Media',
  publisher: 'Publisher',
}

const statusTypeMap: Record<TaskStatus, 'info' | 'warning' | 'success' | 'danger' | ''> = {
  pending: 'info',
  running: 'warning',
  success: 'success',
  failed: 'danger',
  cancelled: '',
}

async function loadProviders() {
  loadingProviders.value = true
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
    loadingProviders.value = false
  }
}

async function loadRecentProjects() {
  loadingProjects.value = true
  try {
    const all = await projectsApi.listProjects()
    recentProjects.value = all.slice(0, 5)
  } catch (e: any) {
    ElMessage.error(`Failed to load projects: ${e.message}`)
  } finally {
    loadingProjects.value = false
  }
}

function goProject(id: string) {
  router.push({ path: '/tasks', query: { id } })
}

function formatDate(s?: string) {
  if (!s) return '-'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString()
}

onMounted(() => {
  loadProviders()
  loadRecentProjects()
})
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">Dashboard</h2>

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="flex-between">
          <span>Registered Providers</span>
          <el-button text :loading="loadingProviders" @click="loadProviders">Refresh</el-button>
        </div>
      </template>
      <div v-loading="loadingProviders">
        <el-empty v-if="groupKeys.length === 0" description="No providers registered" />
        <div v-else class="provider-grid">
          <el-card
            v-for="key in groupKeys"
            :key="key"
            shadow="hover"
            class="provider-group"
          >
            <template #header>
              <span class="group-title">{{ groupLabels[key] || key }}</span>
              <el-tag size="small" type="info" style="margin-left: 8px">
                {{ providerGroups[key].length }}
              </el-tag>
            </template>
            <div
              v-for="p in providerGroups[key]"
              :key="p.name"
              class="provider-item"
            >
              <span class="provider-name">{{ p.name }}</span>
              <el-tag
                size="small"
                :type="p.available ? 'success' : 'danger'"
              >
                {{ p.available ? 'available' : 'unavailable' }}
              </el-tag>
              <el-tag v-if="p.requires_gpu" size="small" type="warning" style="margin-left: 4px">
                GPU
              </el-tag>
            </div>
          </el-card>
        </div>
      </div>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="flex-between">
          <span>Recent Projects</span>
          <el-button text @click="router.push('/tasks')">View All</el-button>
        </div>
      </template>
      <div v-loading="loadingProjects">
        <el-empty v-if="recentProjects.length === 0" description="No projects yet" />
        <el-row v-else :gutter="16">
          <el-col
            v-for="p in recentProjects"
            :key="p.id"
            :xs="24"
            :sm="12"
            :md="8"
          >
            <el-card shadow="hover" class="project-card" @click="goProject(p.id)">
              <div class="flex-between">
                <span class="project-name">{{ p.name }}</span>
                <el-tag size="small" :type="statusTypeMap[p.status] || 'info'">
                  {{ p.status }}
                </el-tag>
              </div>
              <div class="project-topic">{{ p.topic }}</div>
              <el-progress
                :percentage="Math.round((p.progress || 0) * 100)"
                :status="
                  p.status === 'success'
                    ? 'success'
                    : p.status === 'failed'
                    ? 'exception'
                    : undefined
                "
              />
              <div class="project-meta">
                <span>{{ p.current_stage || 'idle' }}</span>
                <span>{{ formatDate(p.created_at) }}</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.provider-group {
  background-color: #fafbfc;
}

.group-title {
  font-weight: 600;
  color: #303133;
}

.provider-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
}
.provider-item:last-child {
  border-bottom: none;
}

.provider-name {
  flex: 1;
  color: #606266;
}

.project-card {
  cursor: pointer;
  margin-bottom: 16px;
  transition: transform 0.15s;
}
.project-card:hover {
  transform: translateY(-2px);
}

.project-name {
  font-weight: 600;
  color: #303133;
}

.project-topic {
  color: #909399;
  font-size: 13px;
  margin: 8px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>

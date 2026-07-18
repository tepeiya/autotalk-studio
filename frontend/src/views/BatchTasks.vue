<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import { useTaskStore } from '@/stores/task'
import { type TaskStatus } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const taskStore = useTaskStore()

const statusFilter = ref<TaskStatus | ''>('')
const polling = ref<number | null>(null)

const selectedId = computed(() => (route.query.id as string) || '')

const statusOptions = [
  { label: 'All', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Running', value: 'running' },
  { label: 'Success', value: 'success' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' },
]

const statusTypeMap: Record<TaskStatus, 'info' | 'warning' | 'success' | 'danger' | ''> = {
  pending: 'info',
  running: 'warning',
  success: 'success',
  failed: 'danger',
  cancelled: '',
}

const filteredProjects = computed(() => projectStore.projects)

async function loadProjects() {
  try {
    await projectStore.fetchProjects(statusFilter.value || undefined)
  } catch (e: any) {
    ElMessage.error(`Failed to load projects: ${e.message}`)
  }
}

function openDetail(id: string) {
  router.push({ path: '/tasks', query: { id } })
}

function backToList() {
  taskStore.stop()
  router.push({ path: '/tasks' })
}

async function cancelProject(id: string) {
  try {
    await ElMessageBox.confirm('Cancel this project?', 'Confirm', { type: 'warning' })
    await projectStore.cancelProject(id)
    ElMessage.success('Cancel requested')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(`Cancel failed: ${e.message}`)
  }
}

async function deleteProject(id: string) {
  try {
    await ElMessageBox.confirm('Delete this project?', 'Confirm', { type: 'warning' })
    await projectStore.deleteProject(id)
    if (selectedId.value === id) backToList()
    ElMessage.success('Deleted')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(`Delete failed: ${e.message}`)
  }
}

function startPolling() {
  stopPolling()
  polling.value = window.setInterval(() => {
    if (!selectedId.value) {
      loadProjects()
    }
  }, 5000)
}

function stopPolling() {
  if (polling.value) {
    clearInterval(polling.value)
    polling.value = null
  }
}

function progressStatus(status: TaskStatus): 'success' | 'exception' | undefined {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}

function formatDate(s?: string) {
  if (!s) return '-'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString()
}

watch(
  selectedId,
  (id) => {
    if (id) {
      taskStore.subscribe(id)
      projectStore.fetchProject(id).catch((e: any) => {
        ElMessage.error(`Failed to load project: ${e.message}`)
      })
    } else {
      taskStore.stop()
      loadProjects()
    }
  },
  { immediate: false }
)

onMounted(() => {
  if (selectedId.value) {
    taskStore.subscribe(selectedId.value)
    projectStore.fetchProject(selectedId.value).catch(() => {
      // ignore
    })
  } else {
    loadProjects()
  }
  startPolling()
})

onUnmounted(() => {
  stopPolling()
  taskStore.stop()
})

async function onFilterChange() {
  if (!selectedId.value) {
    await loadProjects()
  }
}
</script>

<template>
  <div class="page-container">
    <div class="flex-between mb-16">
      <h2 class="page-title" style="margin: 0">Batch Tasks</h2>
      <div v-if="!selectedId" class="flex-row">
        <el-select
          v-model="statusFilter"
          placeholder="Filter by status"
          style="width: 160px"
          @change="onFilterChange"
        >
          <el-option
            v-for="opt in statusOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-button @click="loadProjects">Refresh</el-button>
      </div>
      <el-button v-else :icon="ArrowLeft" @click="backToList">Back to list</el-button>
    </div>

    <!-- List view -->
    <div v-if="!selectedId" v-loading="projectStore.loading">
      <el-empty v-if="filteredProjects.length === 0" description="No projects" />
      <el-row v-else :gutter="16">
        <el-col
          v-for="p in filteredProjects"
          :key="p.id"
          :xs="24"
          :sm="12"
          :md="8"
        >
          <el-card shadow="hover" class="task-card" @click="openDetail(p.id)">
            <div class="flex-between mb-16">
              <span class="task-name">{{ p.name }}</span>
              <el-tag size="small" :type="statusTypeMap[p.status] || 'info'">
                {{ p.status }}
              </el-tag>
            </div>
            <div class="task-topic">{{ p.topic }}</div>
            <el-progress
              :percentage="Math.round((p.progress || 0) * 100)"
              :status="progressStatus(p.status)"
            />
            <div class="task-meta">
              <span>Stage: {{ p.current_stage || 'idle' }}</span>
              <span>{{ formatDate(p.created_at) }}</span>
            </div>
            <div class="task-actions" @click.stop>
              <el-button
                size="small"
                type="warning"
                plain
                :disabled="p.status === 'success' || p.status === 'cancelled'"
                @click="cancelProject(p.id)"
              >
                Cancel
              </el-button>
              <el-button size="small" type="danger" plain @click="deleteProject(p.id)">
                Delete
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- Detail view -->
    <div v-else>
      <el-card class="section-card" shadow="never" v-if="projectStore.selected">
        <template #header>
          <div class="flex-between">
            <span>{{ projectStore.selected.name }} ({{ projectStore.selected.id }})</span>
            <el-tag :type="statusTypeMap[projectStore.selected.status] || 'info'">
              {{ projectStore.selected.status }}
            </el-tag>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Topic">{{ projectStore.selected.topic }}</el-descriptions-item>
          <el-descriptions-item label="Style">{{ projectStore.selected.style }}</el-descriptions-item>
          <el-descriptions-item label="Language">{{ projectStore.selected.language }}</el-descriptions-item>
          <el-descriptions-item label="Duration">{{ projectStore.selected.duration_sec }}s</el-descriptions-item>
          <el-descriptions-item label="Stage">{{ projectStore.selected.current_stage || 'idle' }}</el-descriptions-item>
          <el-descriptions-item label="Created">{{ formatDate(projectStore.selected.created_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="projectStore.selected.output_path" label="Output" :span="2">
            <a :href="`/static/${projectStore.selected.output_path.split('/').pop()}`" target="_blank">
              {{ projectStore.selected.output_path }}
            </a>
          </el-descriptions-item>
          <el-descriptions-item v-if="projectStore.selected.error" label="Error" :span="2">
            <span class="error-text">{{ projectStore.selected.error }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <div class="mt-16">
          <el-progress
            :percentage="Math.round((projectStore.selected.progress || 0) * 100)"
            :status="progressStatus(projectStore.selected.status)"
          />
        </div>
      </el-card>

      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="flex-between">
            <span>Live Event Stream</span>
            <el-tag :type="taskStore.connected ? 'success' : 'info'" size="small">
              {{ taskStore.connected ? 'connected' : 'disconnected' }}
            </el-tag>
          </div>
        </template>
        <div class="event-stream">
          <el-empty v-if="taskStore.events.length === 0" description="No events yet" />
          <div
            v-for="(ev, idx) in taskStore.events"
            :key="idx"
            class="event-row"
          >
            <span class="event-time">{{ formatDate(ev.timestamp) }}</span>
            <el-tag size="small" :type="statusTypeMap[ev.status] || 'info'">{{ ev.status }}</el-tag>
            <el-tag size="small" type="info">{{ ev.stage }}</el-tag>
            <span class="event-progress">{{ Math.round((ev.progress || 0) * 100) }}%</span>
            <span class="event-message">{{ ev.message || '' }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.task-card {
  cursor: pointer;
  margin-bottom: 16px;
  transition: transform 0.15s;
}
.task-card:hover {
  transform: translateY(-2px);
}

.task-name {
  font-weight: 600;
  color: #303133;
}

.task-topic {
  color: #909399;
  font-size: 13px;
  margin-bottom: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.task-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.error-text {
  color: #f56c6c;
  word-break: break-all;
}

.event-stream {
  max-height: 480px;
  overflow-y: auto;
  background-color: #fafbfc;
  border-radius: 4px;
  padding: 8px;
}

.event-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
}
.event-row:last-child {
  border-bottom: none;
}

.event-time {
  color: #909399;
  font-family: monospace;
  font-size: 12px;
  min-width: 180px;
}

.event-progress {
  color: #409eff;
  font-weight: 600;
  min-width: 48px;
}

.event-message {
  color: #606266;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

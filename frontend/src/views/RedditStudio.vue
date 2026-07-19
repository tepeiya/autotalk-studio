<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatLineRound,
  VideoCamera,
  Picture,
  Document,
  Refresh,
  Delete,
  VideoPause,
  Search,
  Promotion,
} from '@element-plus/icons-vue'
import {
  reddit as redditApi,
  type RedditTask,
  type RedditTaskEvent,
  type RedditProvidersResponse,
} from '@/api/client'

// ────────────────────────────────
// State
// ────────────────────────────────

const providers = ref<RedditProvidersResponse | null>(null)
const tasks = ref<RedditTask[]>([])
const loading = ref(false)
const submitting = ref(false)
const selectedTaskId = ref<string | null>(null)
const selectedTask = ref<RedditTask | null>(null)
const events = ref<RedditTaskEvent[]>([])
const activePostTab = ref<string>('')

let evtSource: EventSource | null = null
let pollTimer: number | null = null

const defaultForm = () => ({
  subreddit: 'interestingasfuck',
  limit: 5,
  time_filter: 'day',
  collector: 'reddit_public',
  translator: 'llm',
  image_provider: 'mock',
  note_provider: 'mock',
  generate_image: true,
  generate_note: true,
  generate_video: false,
  publish_to_xiaohongshu: false,
  xiaohongshu_account: 'default',
  // 爆款筛选阈值
  min_score: 1000,
  min_comments: 50,
  min_title_length: 10,
  max_selftext_length: 5000,
  exclude_nsfw: true,
  exclude_stickied: true,
  // LLM 爆款评分
  use_llm_viral_filter: false,
  min_xhs_potential_score: 7,
})
const form = ref(defaultForm())

// ────────────────────────────────
// Computed
// ────────────────────────────────

const collectorOptions = computed(() => providers.value?.collector ?? [])
const translatorOptions = computed(() => providers.value?.translator ?? [])
const imageOptions = computed(() => providers.value?.image ?? [])
const noteOptions = computed(() => providers.value?.note ?? [])

const statusTypeMap: Record<string, string> = {
  pending: 'info',
  collecting: 'warning',
  translating: 'warning',
  generating: 'warning',
  publishing: 'warning',
  success: 'success',
  failed: 'danger',
  cancelled: 'info',
}

function statusType(s: string): string {
  return statusTypeMap[s] || 'info'
}

function viralScoreType(score: number): string {
  if (score >= 9) return 'success'  // 极易爆
  if (score >= 7) return 'success'  // 高潜力
  if (score >= 5) return 'warning'  // 中等
  return 'info'                      // 低
}

const stageLabel: Record<string, string> = {
  collect: '采集',
  translate: '翻译润色',
  image: '生成图片',
  note: '生成笔记',
  video: '生成视频',
  publish: '发布小红书',
  done: '完成',
  error: '错误',
  cancelled: '已取消',
}

function stageText(stage: string | null): string {
  if (!stage) return '-'
  return stageLabel[stage] || stage
}

// 把 /static/xxx 转为浏览器可访问 URL
function assetUrl(path: string): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  if (path.startsWith('/static/')) return path
  if (path.startsWith('/storage/')) return path.replace(/^\/storage\//, '/static/')
  return path
}

// ────────────────────────────────
// API
// ────────────────────────────────

async function loadProviders() {
  try {
    providers.value = await redditApi.listProviders()
  } catch (e: any) {
    ElMessage.error(`加载 providers 失败: ${e.message}`)
  }
}

async function loadTasks() {
  loading.value = true
  try {
    tasks.value = await redditApi.listTasks()
    if (!selectedTaskId.value && tasks.value.length > 0) {
      selectTask(tasks.value[0].id)
    }
  } catch (e: any) {
    ElMessage.error(`加载任务失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

async function submitTask() {
  if (!form.value.subreddit?.trim()) {
    ElMessage.warning('请填写 subreddit')
    return
  }
  submitting.value = true
  try {
    const task = await redditApi.createTask({ ...form.value })
    ElMessage.success(`任务已创建: ${task.id}`)
    await loadTasks()
    selectTask(task.id)
  } catch (e: any) {
    ElMessage.error(`创建失败: ${e.message}`)
  } finally {
    submitting.value = false
  }
}

async function previewCollect() {
  try {
    const result = await redditApi.collect({
      subreddit: form.value.subreddit,
      limit: form.value.limit,
      time_filter: form.value.time_filter,
      collector: form.value.collector,
    })
    ElMessageBox.alert(
      result.posts.map((p) => `• ${p.title}\n  r/${p.subreddit} · score=${p.score}`).join('\n\n'),
      `采集预览（${result.count} 篇）`,
      { customClass: 'reddit-preview-dialog' }
    )
  } catch (e: any) {
    ElMessage.error(`采集失败: ${e.message}`)
  }
}

function selectTask(id: string) {
  selectedTaskId.value = id
  refreshSelected()
  startStream(id)
}

async function refreshSelected() {
  if (!selectedTaskId.value) return
  try {
    const t = await redditApi.getTask(selectedTaskId.value)
    selectedTask.value = t
    // 同步回 tasks 列表
    const idx = tasks.value.findIndex((x) => x.id === t.id)
    if (idx >= 0) tasks.value[idx] = t
  } catch (e: any) {
    // 静默
  }
}

async function cancelTask(id: string) {
  try {
    await redditApi.cancelTask(id)
    ElMessage.success('已请求取消')
    refreshSelected()
  } catch (e: any) {
    ElMessage.error(`取消失败: ${e.message}`)
  }
}

async function removeTask(id: string) {
  try {
    await ElMessageBox.confirm('确认删除该任务及其产物？', '删除确认', { type: 'warning' })
    await redditApi.deleteTask(id)
    if (selectedTaskId.value === id) {
      selectedTaskId.value = null
      selectedTask.value = null
      stopStream()
    }
    ElMessage.success('已删除')
    await loadTasks()
  } catch (e: any) {
    if (e !== 'cancel' && e?.message) ElMessage.error(`删除失败: ${e.message}`)
  }
}

// ────────────────────────────────
// SSE
// ────────────────────────────────

function startStream(id: string) {
  stopStream()
  evtSource = redditApi.streamEvents(id)
  evtSource.addEventListener('message', (ev: MessageEvent) => {
    try {
      const data: RedditTaskEvent = JSON.parse(ev.data)
      events.value.push(data)
      // 限制长度
      if (events.value.length > 200) events.value = events.value.slice(-200)
      // 实时刷新 task
      refreshSelected()
    } catch {
      // ignore parse errors
    }
  })
  evtSource.onerror = () => {
    // 浏览器会自动重连，无需处理
  }
}

function stopStream() {
  if (evtSource) {
    evtSource.close()
    evtSource = null
  }
}

// 后备轮询（SSE 异常时）
function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(() => {
    if (selectedTaskId.value) refreshSelected()
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ────────────────────────────────
// Lifecycle
// ────────────────────────────────

onMounted(async () => {
  await Promise.all([loadProviders(), loadTasks()])
  startPolling()
})

onBeforeUnmount(() => {
  stopStream()
  stopPolling()
})

// 当切换任务时清空事件
watch(selectedTaskId, () => {
  events.value = []
})

// 当任务完成时，自动选中第一个 post tab
watch(selectedTask, (t) => {
  if (t && t.posts.length > 0 && !activePostTab.value) {
    activePostTab.value = t.posts[0].post_id
  }
})
</script>

<template>
  <div class="reddit-studio">
    <!-- 顶部：创建任务 -->
    <el-card class="form-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><ChatLineRound /></el-icon>
          <span>Reddit → 小红书 爆款生产线</span>
          <el-tag size="small" type="success" effect="plain">独立业务线</el-tag>
        </div>
      </template>

      <el-form :model="form" label-width="120px" label-position="right">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="Subreddit">
              <el-input v-model="form.subreddit" placeholder="interestingasfuck">
                <template #prepend>r/</template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="采集数量">
              <el-input-number v-model="form.limit" :min="1" :max="20" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="时间范围">
              <el-select v-model="form.time_filter">
                <el-option label="day" value="day" />
                <el-option label="week" value="week" />
                <el-option label="month" value="month" />
                <el-option label="year" value="year" />
                <el-option label="all" value="all" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="Collector">
              <el-select v-model="form.collector">
                <el-option
                  v-for="c in collectorOptions"
                  :key="c.name"
                  :label="c.name"
                  :value="c.name"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="Translator">
              <el-select v-model="form.translator">
                <el-option
                  v-for="t in translatorOptions"
                  :key="t.name"
                  :label="t.name"
                  :value="t.name"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="Image">
              <el-select v-model="form.image_provider">
                <el-option
                  v-for="i in imageOptions"
                  :key="i.name"
                  :label="i.name"
                  :value="i.name"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Note">
              <el-select v-model="form.note_provider">
                <el-option
                  v-for="n in noteOptions"
                  :key="n.name"
                  :label="n.name"
                  :value="n.name"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生成项">
              <el-checkbox v-model="form.generate_image">
                <el-icon><Picture /></el-icon> 图片
              </el-checkbox>
              <el-checkbox v-model="form.generate_note">
                <el-icon><Document /></el-icon> 笔记
              </el-checkbox>
              <el-checkbox v-model="form.generate_video">
                <el-icon><VideoCamera /></el-icon> 视频（较慢）
              </el-checkbox>
              <el-checkbox v-model="form.publish_to_xiaohongshu">
                <el-icon><Promotion /></el-icon> 发布到小红书
              </el-checkbox>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 爆款筛选 -->
        <el-divider content-position="left">
          <span class="divider-title">🔥 爆款筛选</span>
        </el-divider>
        <el-row :gutter="16">
          <el-col :span="4">
            <el-form-item label="最低点赞">
              <el-input-number v-model="form.min_score" :min="0" :step="100" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="最低评论">
              <el-input-number v-model="form.min_comments" :min="0" :step="10" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="标题最短">
              <el-input-number v-model="form.min_title_length" :min="0" :max="300" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="正文最长">
              <el-input-number v-model="form.max_selftext_length" :min="100" :step="500" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="排除 NSFW">
              <el-switch v-model="form.exclude_nsfw" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="排除置顶">
              <el-switch v-model="form.exclude_stickied" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="LLM 评分">
              <el-switch v-model="form.use_llm_viral_filter" />
              <small class="hint-text">启用后 LLM 评估 1-10 分爆款潜力</small>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="最低潜力分">
              <el-input-number
                v-model="form.min_xhs_potential_score"
                :min="0"
                :max="10"
                :disabled="!form.use_llm_viral_filter"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row>
          <el-col :span="24" style="text-align: right">
            <el-button :icon="Search" @click="previewCollect">采集预览</el-button>
            <el-button
              type="primary"
              :icon="Promotion"
              :loading="submitting"
              @click="submitTask"
            >
              创建任务并运行
            </el-button>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card class="list-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>任务列表</span>
          <el-button :icon="Refresh" size="small" link @click="loadTasks">刷新</el-button>
        </div>
      </template>
      <el-table
        :data="tasks"
        v-loading="loading"
        size="small"
        @row-click="(row: RedditTask) => selectTask(row.id)"
        highlight-current-row
        :row-class-name="({ row }) => (row.id === selectedTaskId ? 'is-selected' : '')"
      >
        <el-table-column prop="id" label="ID" width="180" />
        <el-table-column label="Subreddit" width="140">
          <template #default="{ row }">
            <el-tag size="small" type="info">r/{{ row.params?.subreddit || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="阶段" width="120">
          <template #default="{ row }">
            {{ stageText(row.current_stage) }}
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress :percentage="Math.round((row.progress || 0) * 100)" :status="
              row.status === 'success' ? 'success' :
              row.status === 'failed' ? 'exception' :
              row.status === 'cancelled' ? 'exception' : undefined
            " />
          </template>
        </el-table-column>
        <el-table-column label="产物" width="180">
          <template #default="{ row }">
            <el-tag size="small" type="info">帖 {{ row.posts?.length || 0 }}</el-tag>
            <el-tag size="small" type="info">图 {{ row.images?.length || 0 }}</el-tag>
            <el-tag size="small" type="info">笔 {{ row.notes?.length || 0 }}</el-tag>
            <el-tag size="small" type="info">视 {{ row.videos?.length || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="筛选参数" width="200">
          <template #default="{ row }">
            <el-tag v-if="row.params?.min_score > 0" size="small" type="warning" effect="plain">
              ≥{{ row.params.min_score }} 赞
            </el-tag>
            <el-tag v-if="row.params?.use_llm_viral_filter" size="small" type="success" effect="plain">
              LLM ≥{{ row.params.min_xhs_potential_score }}
            </el-tag>
            <span v-if="!row.params?.min_score && !row.params?.use_llm_viral_filter" class="muted-text">
              无阈值
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="warning"
              :icon="VideoPause"
              link
              :disabled="!['pending','collecting','translating','generating','publishing'].includes(row.status)"
              @click.stop="cancelTask(row.id)"
            >取消</el-button>
            <el-button
              size="small"
              type="danger"
              :icon="Delete"
              link
              @click.stop="removeTask(row.id)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 任务详情 -->
    <el-card v-if="selectedTask" class="detail-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>任务详情 · {{ selectedTask.id }}</span>
          <div>
            <el-tag size="small" :type="statusType(selectedTask.status)">{{ selectedTask.status }}</el-tag>
            <el-button :icon="Refresh" size="small" link @click="refreshSelected">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 事件流 -->
      <el-tabs v-model="activePostTab" type="border-card">
        <el-tab-pane label="事件流" name="__events">
          <div class="event-list">
            <div v-for="(ev, idx) in events" :key="idx" class="event-row">
              <el-tag size="small" :type="statusType(ev.status)">{{ ev.status }}</el-tag>
              <span class="event-stage">{{ stageText(ev.stage) }}</span>
              <span class="event-msg">{{ ev.message || '' }}</span>
              <span class="event-time">{{ ev.timestamp?.slice(11, 19) }}</span>
              <el-tag v-if="ev.post_id" size="small" type="info" effect="plain">{{ ev.post_id }}</el-tag>
            </div>
            <div v-if="events.length === 0" class="empty-tip">暂无事件，等待 SSE 推送...</div>
          </div>
        </el-tab-pane>

        <!-- 每篇 post 一个 tab -->
        <el-tab-pane
          v-for="post in selectedTask.posts"
          :key="post.post_id"
          :label="post.post_id"
          :name="post.post_id"
        >
          <div class="post-detail">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="原帖标题" :span="2">
                <a v-if="post.url" :href="post.url" target="_blank" rel="noopener">
                  {{ post.title }}
                </a>
                <span v-else>{{ post.title }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="subreddit">
                r/{{ post.subreddit }}
              </el-descriptions-item>
              <el-descriptions-item label="author">
                {{ post.author || 'unknown' }}
              </el-descriptions-item>
              <el-descriptions-item label="score">{{ post.score }}</el-descriptions-item>
              <el-descriptions-item label="comments">{{ post.num_comments }}</el-descriptions-item>
            </el-descriptions>

            <!-- 翻译润色 -->
            <template v-for="t in selectedTask.translated.filter(t => t.post_id === post.post_id)" :key="t.post_id">
              <h4 class="section-title">📝 翻译润色后</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="中文标题">
                  <strong>{{ t.title_cn }}</strong>
                </el-descriptions-item>
                <el-descriptions-item label="摘要">{{ t.summary_cn }}</el-descriptions-item>
                <el-descriptions-item label="正文">
                  <pre class="body-cn">{{ t.body_cn }}</pre>
                </el-descriptions-item>
                <el-descriptions-item label="关键点">
                  <ul>
                    <li v-for="(p, i) in t.key_points" :key="i">{{ p }}</li>
                  </ul>
                </el-descriptions-item>
                <el-descriptions-item label="标签">
                  <el-tag v-for="(tag, i) in t.tags" :key="i" size="small" type="success" effect="plain" class="tag">#{{ tag }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="爆款潜力">
                  <el-tag
                    v-if="t.xhs_potential_score !== undefined && t.xhs_potential_score > 0"
                    :type="viralScoreType(t.xhs_potential_score)"
                    size="small"
                  >
                    {{ t.xhs_potential_score }}/10
                  </el-tag>
                  <el-tag v-else size="small" type="info">未评分</el-tag>
                  <el-tag
                    v-if="t.is_xhs_friendly === false"
                    size="small"
                    type="danger"
                    effect="plain"
                  >
                    ⚠️ 不适合发小红书
                  </el-tag>
                  <span v-if="t.viral_reason" class="viral-reason">{{ t.viral_reason }}</span>
                </el-descriptions-item>
              </el-descriptions>
            </template>

            <!-- 生成的图片 -->
            <template v-for="img in selectedTask.images.filter(i => i.post_id === post.post_id)" :key="img.post_id">
              <h4 class="section-title">🖼️ 生成图片</h4>
              <div class="image-grid">
                <div class="image-cell">
                  <el-image
                    :src="assetUrl(img.url)"
                    fit="contain"
                    style="max-width: 300px; max-height: 300px; border: 1px solid #eee"
                    :preview-src-list="[assetUrl(img.url)]"
                  />
                  <div class="image-meta">
                    <small>{{ img.width }}x{{ img.height }}</small>
                    <a :href="assetUrl(img.url)" target="_blank" rel="noopener">下载原图</a>
                  </div>
                </div>
              </div>
            </template>

            <!-- 小红书笔记 -->
            <template v-for="note in selectedTask.notes.filter(n => n.post_id === post.post_id)" :key="note.post_id">
              <h4 class="section-title">📕 小红书笔记</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="标题">
                  <strong>{{ note.title }}</strong>
                </el-descriptions-item>
                <el-descriptions-item label="正文">
                  <pre class="body-cn">{{ note.body }}</pre>
                </el-descriptions-item>
                <el-descriptions-item label="标签">
                  <el-tag v-for="(tag, i) in note.tags" :key="i" size="small" type="success" effect="plain" class="tag">#{{ tag }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="原文件">
                  <a :href="assetUrl(note.url)" target="_blank" rel="noopener">{{ note.note_path }}</a>
                </el-descriptions-item>
              </el-descriptions>
            </template>

            <!-- 视频 -->
            <template v-for="vid in selectedTask.videos.filter(v => v.post_id === post.post_id)" :key="vid.post_id">
              <h4 class="section-title">🎬 视频</h4>
              <video
                :src="assetUrl(vid.url)"
                controls
                style="max-width: 100%; max-height: 400px"
              />
              <div>
                <a :href="assetUrl(vid.url)" target="_blank" rel="noopener">下载视频</a>
              </div>
            </template>
          </div>
        </el-tab-pane>
      </el-tabs>

      <el-alert
        v-if="selectedTask.error"
        type="error"
        :title="selectedTask.error"
        :closable="false"
        style="margin-top: 12px"
      />
    </el-card>

    <el-empty v-else description="选择一个任务查看详情" />
  </div>
</template>

<style scoped>
.reddit-studio {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.card-header span:first-child,
.card-header > span {
  flex: 1;
}

.list-card :deep(.el-table__row) {
  cursor: pointer;
}

.list-card :deep(.el-table__row.is-selected) {
  background-color: var(--el-color-primary-light-9) !important;
}

.event-list {
  max-height: 360px;
  overflow-y: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

.event-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.event-stage {
  color: #409eff;
  min-width: 80px;
}

.event-msg {
  flex: 1;
  color: #606266;
}

.event-time {
  color: #909399;
}

.empty-tip {
  color: #909399;
  text-align: center;
  padding: 16px;
}

.post-detail {
  padding: 8px 4px;
}

.section-title {
  margin: 16px 0 8px;
  font-size: 14px;
  color: #303133;
  border-left: 3px solid var(--el-color-primary);
  padding-left: 8px;
}

.body-cn {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
}

.tag {
  margin-right: 4px;
  margin-bottom: 4px;
}

.image-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.image-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.image-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.divider-title {
  font-weight: 600;
  color: var(--el-color-warning);
}

.hint-text {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}

.muted-text {
  color: #c0c4cc;
  font-size: 12px;
}

.viral-reason {
  margin-left: 8px;
  color: #606266;
  font-size: 12px;
}
</style>

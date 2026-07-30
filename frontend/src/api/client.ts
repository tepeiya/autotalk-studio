import axios, { type AxiosInstance } from 'axios'

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error?.response?.data?.detail || error?.message || 'Request failed'
    return Promise.reject(new Error(message))
  }
)

// ────────────────────────────────
// 类型（与后端 schemas 对齐，宽松定义）
// ────────────────────────────────

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed'
  | 'cancelled'
  // 新增：预览 + 审批流
  | 'previewing'
  | 'previewed'
  | 'approved'
  | 'rejected'

export interface ProviderInfo {
  name: string
  type: string
  requires_gpu?: boolean
  available?: boolean
  config_schema?: Record<string, any>
}

// ────────────── 预检 / 费用 / 审批相关类型 ──────────────
export interface PreflightIssue {
  level: 'error' | 'warning' | 'info'
  code: string
  message: string
  field?: string | null
}

export interface PreflightResult {
  passed: boolean
  summary: string
  issues: PreflightIssue[]
  error_count: number
  warning_count: number
  info_count: number
}

export interface CostEstimateItem {
  provider: string
  stage: string
  unit: string
  estimated_units: number
  unit_cost_cny: number
  estimated_cost_cny: number
  note?: string | null
}

export interface CostEstimateResult {
  items: CostEstimateItem[]
  total_cny: number
  currency: string
  confidence: 'exact' | 'rough' | 'unknown'
  summary: string
}

export interface ProjectApproveRequest {
  approved: boolean
  reason?: string | null
  override_duration_sec?: number | null
}

export interface ProjectCreatePayload {
  name: string
  topic: string
  style?: string
  duration_sec?: number
  language?: string
  orientation?: string
  llm_provider?: string | null
  tts_provider?: string | null
  voice_id?: string | null
  avatar_provider?: string | null
  avatar_id?: string | null
  bgm_mode?: string
  bgm_id?: string | null
  bg_mode?: string
  reference_text?: string | null
  auto_publish?: boolean
  publish_platforms?: string[]
  // 新增（预览 + 预检 + 费用确认，默认 false，完全兼容旧代码）
  enable_preview_approval?: boolean
  preview_duration_sec?: number
  require_asset_preflight?: boolean
  require_cost_confirmation?: boolean
}

export interface Project extends ProjectCreatePayload {
  id: string
  status: TaskStatus
  progress: number
  current_stage: string | null
  script?: any
  output_path?: string | null
  preview_output_path?: string | null
  error?: string | null
  created_at?: string
  updated_at?: string
}

export interface TaskEvent {
  project_id: string
  stage: string
  status: TaskStatus
  progress: number
  message?: string | null
  timestamp: string
}

export interface VoiceProfile {
  id: string
  name: string
  provider: string
  sample_path?: string | null
  description?: string | null
  created_at?: string
}

export interface SynthesizePayload {
  text: string
  voice_id: string
  speed?: number
  pitch?: number
}

export interface SynthesizeResult {
  audio_path: string
  audio_url: string
}

export interface AvatarProfile {
  id: string
  name: string
  provider: string
  portrait_path: string
  description?: string | null
  created_at?: string
}

export interface AvatarRenderResult {
  video_path: string
  video_url: string
}

export interface MediaItem {
  id: string
  type: string
  name: string
  path: string
  tags?: string[]
}

export interface PublishResult {
  [key: string]: any
}

export interface PublisherPlatform {
  name: string
  requires_gpu?: boolean
  class?: string
  config_schema?: Record<string, any>
}

export interface GeneratedVideo {
  id: string
  filename: string
  path: string
  url: string
  size_bytes: number
  modified_at: number
}

export interface PublishedVideo {
  id: string
  filename: string
  path: string
  url: string
  size_bytes: number
  modified_at: number
  platform: string
}

export interface CookieEntry {
  platform: string
  account: string
  path: string
  size_bytes: number
  modified_at: number
}

export interface CookieStatus {
  sau_path: string
  cookies: CookieEntry[]
  hint?: string
}

export interface SupportedPlatforms {
  sau_installed: boolean
  sau_project_path: string
  platforms: Array<{ name: string; sau_name: string; display: string }>
}

// ────────────────────────────────
// Projects
// ────────────────────────────────

export const projects = {
  createProject(payload: ProjectCreatePayload) {
    return client.post<Project>('/projects', payload).then((r) => r.data)
  },
  listProjects(status?: TaskStatus | string) {
    return client
      .get<Project[]>('/projects', { params: status ? { status } : {} })
      .then((r) => r.data)
  },
  getProject(id: string) {
    return client.get<Project>(`/projects/${id}`).then((r) => r.data)
  },
  cancelProject(id: string) {
    return client.post<{ cancelled: boolean }>(`/projects/${id}/cancel`).then((r) => r.data)
  },
  deleteProject(id: string) {
    return client.delete<{ deleted: string }>(`/projects/${id}`).then((r) => r.data)
  },
  // ────── 新增（预检 / 费用 / 预览 / 审批）──────
  preflight(payload: ProjectCreatePayload) {
    return client.post<PreflightResult>('/projects/preflight', payload).then((r) => r.data)
  },
  estimateCost(payload: ProjectCreatePayload) {
    return client.post<CostEstimateResult>('/projects/cost', payload).then((r) => r.data)
  },
  // 增强型创建（可触发预检阻塞、预览-审批流）
  createProjectWithChecks(payload: ProjectCreatePayload) {
    return client.post<Project>('/projects/_create_with_checks', payload).then((r) => r.data)
  },
  runPreview(id: string) {
    return client.post<Project>(`/projects/${id}/preview`).then((r) => r.data)
  },
  approve(id: string, body: ProjectApproveRequest) {
    return client.post<Project>(`/projects/${id}/approve`, body).then((r) => r.data)
  },
}

// ────────────────────────────────
// Tasks (SSE)
// ────────────────────────────────

export const tasks = {
  listEvents(id: string) {
    return client.get<TaskEvent[]>(`/tasks/${id}/events`).then((r) => r.data)
  },
  streamEvents(id: string): EventSource {
    return new EventSource(`/api/tasks/${id}/stream`)
  },
}

// ────────────────────────────────
// Voices
// ────────────────────────────────

export const voices = {
  listVoices() {
    return client.get<VoiceProfile[]>('/voices').then((r) => r.data)
  },
  cloneVoice(formData: FormData) {
    return client
      .post<VoiceProfile>('/voices/clone', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
  synthesize(payload: SynthesizePayload, provider?: string) {
    return client
      .post<SynthesizeResult>('/voices/synthesize', payload, {
        params: provider ? { provider } : {},
      })
      .then((r) => r.data)
  },
}

// ────────────────────────────────
// Avatars
// ────────────────────────────────

export const avatars = {
  listAvatars() {
    return client.get<AvatarProfile[]>('/avatars').then((r) => r.data)
  },
  register(formData: FormData) {
    return client
      .post<AvatarProfile>('/avatars/register', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
  render(formData: FormData) {
    return client
      .post<AvatarRenderResult>('/avatars/render', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
}

// ────────────────────────────────
// Media
// ────────────────────────────────

export const media = {
  listBgm() {
    return client.get<MediaItem[]>('/media/bgm').then((r) => r.data)
  },
  listBackgrounds() {
    return client.get<MediaItem[]>('/media/backgrounds').then((r) => r.data)
  },
  uploadBgm(formData: FormData) {
    return client
      .post<MediaItem>('/media/bgm/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
  uploadBackground(formData: FormData) {
    return client
      .post<MediaItem>('/media/backgrounds/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
}

// ────────────────────────────────
// Publishers
// ────────────────────────────────

export const publishers = {
  listPlatforms() {
    return client.get<PublisherPlatform[]>('/publishers/platforms').then((r) => r.data)
  },
  listSupportedPlatforms() {
    return client.get<SupportedPlatforms>('/publishers/supported-platforms').then((r) => r.data)
  },
  listVideos() {
    return client.get<GeneratedVideo[]>('/publishers/videos').then((r) => r.data)
  },
  listPublished() {
    return client.get<PublishedVideo[]>('/publishers/published').then((r) => r.data)
  },
  listCookies() {
    return client.get<CookieStatus>('/publishers/cookies').then((r) => r.data)
  },
  triggerLogin(formData: FormData) {
    return client
      .post<{ platform: string; account: string; status: string; hint?: string; cmd?: string }>(
        '/publishers/login',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 30000 }
      )
      .then((r) => r.data)
  },
  publish(formData: FormData) {
    return client
      .post<PublishResult>('/publishers/publish', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 600000, // 真实上传可能耗时较长
      })
      .then((r) => r.data)
  },
}

// ────────────────────────────────
// Providers
// ────────────────────────────────

export const providers = {
  listProviders(type?: string) {
    return client
      .get<ProviderInfo[]>('/providers', { params: type ? { type } : {} })
      .then((r) => r.data)
  },
}

export interface SettingsSnapshot {
  host: string
  port: number
  cors_origins: string
  storage_root: string
  llm: Record<string, any>
  tts: Record<string, any>
  avatar: Record<string, any>
  media: Record<string, any>
  publisher: Record<string, any>
  pipeline: Record<string, any>
  yaml_path: string
}

export type SettingsPatch = Partial<Pick<SettingsSnapshot, 'host' | 'port' | 'cors_origins' | 'storage_root'>> & {
  llm?: Record<string, any>
  tts?: Record<string, any>
  avatar?: Record<string, any>
  media?: Record<string, any>
  publisher?: Record<string, any>
  pipeline?: Record<string, any>
}

// ────────────────────────────────
// Settings（后端真实配置：GET + PATCH /api/settings）
// ────────────────────────────────

export const settings = {
  fetchSnapshot() {
    return client.get<SettingsSnapshot>('/settings').then((r) => r.data)
  },
  updateSnapshot(patch: SettingsPatch) {
    return client.patch<SettingsSnapshot>('/settings', patch).then((r) => r.data)
  },
  async fetchProviders() {
    const list = await providers.listProviders()
    const grouped: Record<string, ProviderInfo[]> = {}
    for (const p of list) {
      if (!grouped[p.type]) grouped[p.type] = []
      grouped[p.type].push(p)
    }
    return grouped
  },
}

// ────────────────────────────────
// Reddit 业务线
// ────────────────────────────────

export type RedditTaskStatus =
  | 'pending'
  | 'collecting'
  | 'translating'
  | 'generating'
  | 'publishing'
  | 'success'
  | 'failed'
  | 'cancelled'

export interface RedditHotPost {
  post_id: string
  title: string
  selftext: string
  subreddit: string
  author: string
  score: number
  num_comments: number
  url: string
  permalink: string
  created_utc: number
  over_18?: boolean
  stickied?: boolean
  collected_at?: string
}

export interface TranslatedPost {
  post_id: string
  original_title: string
  original_text: string
  title_cn: string
  summary_cn: string
  body_cn: string
  key_points: string[]
  tags: string[]
  is_xhs_friendly?: boolean
  xhs_potential_score?: number
  viral_reason?: string
}

export interface RedditImageArtifact {
  post_id: string
  image_path: string
  url: string
  prompt: string
  width: number
  height: number
}

export interface RedditNoteArtifact {
  post_id: string
  note_path: string
  url: string
  title: string
  body: string
  tags: string[]
  image_paths: string[]
}

export interface RedditVideoArtifact {
  post_id: string
  video_path: string
  url: string
  script?: any
}

export interface RedditTaskCreatePayload {
  subreddit?: string
  limit?: number
  time_filter?: string
  collector?: string
  translator?: string
  image_provider?: string
  note_provider?: string
  generate_image?: boolean
  generate_note?: boolean
  generate_video?: boolean
  publish_to_xiaohongshu?: boolean
  xiaohongshu_account?: string
  // 爆款筛选
  min_score?: number
  min_comments?: number
  min_title_length?: number
  max_selftext_length?: number
  exclude_nsfw?: boolean
  exclude_stickied?: boolean
  // LLM 爆款评分
  use_llm_viral_filter?: boolean
  min_xhs_potential_score?: number
}

export interface RedditTask {
  id: string
  params: RedditTaskCreatePayload
  status: RedditTaskStatus
  progress: number
  current_stage: string | null
  posts: RedditHotPost[]
  translated: TranslatedPost[]
  images: RedditImageArtifact[]
  notes: RedditNoteArtifact[]
  videos: RedditVideoArtifact[]
  error: string | null
  created_at: string
  updated_at: string
}

export interface RedditTaskEvent {
  task_id: string
  stage: string
  status: RedditTaskStatus
  progress: number
  message?: string | null
  post_id?: string | null
  timestamp: string
}

export interface RedditProvidersResponse {
  collector: Array<{ name: string; class: string; requires_gpu: boolean }>
  translator: Array<{ name: string; class: string; requires_gpu: boolean }>
  image: Array<{ name: string; class: string; requires_gpu: boolean }>
  note: Array<{ name: string; class: string; requires_gpu: boolean }>
}

export interface RedditNoteContent {
  task_id: string
  post_id: string
  path: string
  url: string
  content: string
}

export interface RedditCollectResponse {
  subreddit: string
  count: number
  posts: RedditHotPost[]
}

export interface RedditOkResponse {
  ok: boolean
  task_id?: string
}

export const reddit = {
  listProviders() {
    return client.get<RedditProvidersResponse>('/reddit/providers').then((r) => r.data)
  },
  collect(payload: { subreddit: string; limit?: number; time_filter?: string; collector?: string }) {
    return client
      .post<RedditCollectResponse>('/reddit/collect', payload)
      .then((r) => r.data)
  },
  createTask(payload: RedditTaskCreatePayload) {
    return client.post<RedditTask>('/reddit/tasks', payload).then((r) => r.data)
  },
  listTasks() {
    return client.get<RedditTask[]>('/reddit/tasks').then((r) => r.data)
  },
  getTask(id: string) {
    return client.get<RedditTask>(`/reddit/tasks/${id}`).then((r) => r.data)
  },
  cancelTask(id: string) {
    return client
      .post<RedditOkResponse>(`/reddit/tasks/${id}/cancel`)
      .then((r) => r.data)
  },
  deleteTask(id: string) {
    return client.delete<RedditOkResponse>(`/reddit/tasks/${id}`).then((r) => r.data)
  },
  listEvents(id: string) {
    return client.get<RedditTaskEvent[]>(`/reddit/tasks/${id}/events`).then((r) => r.data)
  },
  streamEvents(id: string): EventSource {
    return new EventSource(`/api/reddit/tasks/${id}/stream`)
  },
  getNote(taskId: string, postId: string) {
    return client
      .get<RedditNoteContent>(`/reddit/notes/${taskId}/${postId}`)
      .then((r) => r.data)
  },
}

export default client

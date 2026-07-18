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

export interface ProviderInfo {
  name: string
  type: string
  requires_gpu?: boolean
  available?: boolean
  config_schema?: Record<string, any>
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
}

export interface Project extends ProjectCreatePayload {
  id: string
  status: TaskStatus
  progress: number
  current_stage: string | null
  script?: any
  output_path?: string | null
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
  publish(formData: FormData) {
    return client
      .post<PublishResult>('/publishers/publish', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
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

// ────────────────────────────────
// Settings（前端组装：基于 providers）
// ────────────────────────────────

export const settings = {
  async fetch() {
    const list = await providers.listProviders()
    const grouped: Record<string, ProviderInfo[]> = {}
    for (const p of list) {
      if (!grouped[p.type]) grouped[p.type] = []
      grouped[p.type].push(p)
    }
    return grouped
  },
}

export default client

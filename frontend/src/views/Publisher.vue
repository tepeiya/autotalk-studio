<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion, VideoCamera, Check, Refresh, Key, UploadFilled } from '@element-plus/icons-vue'
import {
  publishers as publishersApi,
  type GeneratedVideo,
  type PublishedVideo,
  type PublisherPlatform,
  type CookieStatus,
  type SupportedPlatforms,
} from '@/api/client'

const videos = ref<GeneratedVideo[]>([])
const published = ref<PublishedVideo[]>([])
const platforms = ref<PublisherPlatform[]>([])
const supported = ref<SupportedPlatforms | null>(null)
const cookieStatus = ref<CookieStatus | null>(null)
const loading = ref(false)

// 发布对话框
const publishDialogVisible = ref(false)
const publishing = ref(false)
const currentVideo = ref<GeneratedVideo | null>(null)
const publishForm = ref({
  platform: 'dummy',
  account: 'default',
  title: '',
  description: '',
  tags: '',
})

// 登录对话框
const loginDialogVisible = ref(false)
const logging = ref(false)
const loginForm = ref({
  platform: 'douyin',
  account: 'default',
})

async function loadAll() {
  loading.value = true
  try {
    const [v, p, plat, sup, ck] = await Promise.all([
      publishersApi.listVideos(),
      publishersApi.listPublished(),
      publishersApi.listPlatforms(),
      publishersApi.listSupportedPlatforms(),
      publishersApi.listCookies(),
    ])
    videos.value = v
    published.value = p
    platforms.value = plat
    supported.value = sup
    cookieStatus.value = ck
  } catch (e: any) {
    ElMessage.error(`加载失败: ${e.message}`)
  } finally {
    loading.value = false
  }
}

async function reloadCookies() {
  try {
    cookieStatus.value = await publishersApi.listCookies()
    ElMessage.success('Cookie 状态已刷新')
  } catch (e: any) {
    ElMessage.error(`刷新失败: ${e.message}`)
  }
}

function openPublishDialog(video: GeneratedVideo) {
  currentVideo.value = video
  publishForm.value = {
    platform: 'dummy',
    account: 'default',
    title: video.filename.replace(/\.mp4$/i, ''),
    description: '',
    tags: '',
  }
  publishDialogVisible.value = true
}

function openLoginDialog() {
  loginForm.value = { platform: 'douyin', account: 'default' }
  loginDialogVisible.value = true
}

async function doLogin() {
  logging.value = true
  try {
    const fd = new FormData()
    fd.append('platform', loginForm.value.platform)
    fd.append('account', loginForm.value.account)
    const result = await publishersApi.triggerLogin(fd)
    if (result.status === 'browser_started') {
      ElMessageBox.alert(
        `${result.hint || '浏览器已启动'}\n\n执行命令: ${result.cmd || ''}\n\n请在浏览器中完成扫码登录，登录成功后点击"我已完成登录"刷新 cookie 状态。`,
        '浏览器已启动',
        { confirmButtonText: '我已完成登录', type: 'info' }
      ).then(() => reloadCookies()).catch(() => {})
    } else {
      ElMessage.success(`登录流程结束 (status=${result.status})`)
      await reloadCookies()
    }
    loginDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(`登录失败: ${e.message}`)
  } finally {
    logging.value = false
  }
}

async function doPublish() {
  if (!currentVideo.value) return
  if (!publishForm.value.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  publishing.value = true
  try {
    const fd = new FormData()
    fd.append('video_path', currentVideo.value.path)
    fd.append('title', publishForm.value.title.trim())
    fd.append('description', publishForm.value.description)
    fd.append('tags', publishForm.value.tags)
    fd.append('platform', publishForm.value.platform)
    fd.append('account', publishForm.value.account)
    const result = await publishersApi.publish(fd)
    ElMessage.success(`发布成功 [${result.platform}]`)
    publishDialogVisible.value = false
    await loadAll()
  } catch (e: any) {
    ElMessage.error(`发布失败: ${e.message}`)
  } finally {
    publishing.value = false
  }
}

async function copyPath(p: string) {
  try {
    await navigator.clipboard.writeText(p)
    ElMessage.success('路径已复制')
  } catch {
    ElMessage.warning('复制失败')
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDate(ts: number) {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString()
}

function cookiePlatformTag(p: string): string {
  const m: Record<string, string> = {
    douyin: '抖音', bilibili: 'B站', kuaishou: '快手',
    xiaohongshu: '小红书', tencent: '视频号', baijiahao: '百家号',
    tiktok: 'TikTok', youtube: 'YouTube',
  }
  return m[p] || p
}

const platformOptions = computed(() => {
  const opts = [{ label: 'dummy (本地复制测试)', value: 'dummy' }]
  if (supported.value) {
    for (const p of supported.value.platforms) {
      opts.push({ label: `${p.name} (${cookiePlatformTag(p.name)})`, value: p.name })
    }
  }
  return opts
})

onMounted(loadAll)
</script>

<template>
  <div class="page-container">
    <div class="flex-between mb-16">
      <h2 class="page-title" style="margin: 0">Publisher</h2>
      <div class="flex-row">
        <el-button :icon="Key" @click="openLoginDialog">扫码登录</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">Refresh</el-button>
      </div>
    </div>

    <el-alert
      class="mb-16"
      :type="supported?.sau_installed ? 'success' : 'warning'"
      :closable="false"
      :title="supported?.sau_installed ? 'social-auto-upload 已集成' : 'social-auto-upload 未安装'"
    >
      <template #description>
        <div v-if="supported?.sau_installed">
          项目路径: <code>{{ supported?.sau_project_path }}</code>，支持真实发布到抖音/B站/快手/小红书等
        </div>
        <div v-else>
          当前只能用 dummy 本地复制。要发布到真实平台，请 clone
          <a href="https://github.com/dreammis/social-auto-upload" target="_blank">social-auto-upload</a>
          到 <code>{{ supported?.sau_project_path }}</code>，安装 playwright，然后点击"扫码登录"获取 cookie。
        </div>
      </template>
    </el-alert>

    <!-- 已注册平台 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="flex-between">
          <span>已注册 Publisher</span>
          <el-tag size="small">{{ platforms.length }} 个</el-tag>
        </div>
      </template>
      <el-empty v-if="platforms.length === 0" description="无" />
      <el-tag
        v-for="p in platforms"
        :key="p.name"
        class="platform-tag"
        :type="p.name === 'dummy' ? 'info' : 'success'"
      >
        {{ p.name }}
        <span class="platform-class">({{ p.class }})</span>
        <span v-if="p.healthy === false" class="platform-class">⚠️ 未就绪</span>
      </el-tag>
    </el-card>

    <!-- Cookie 状态 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="flex-between">
          <span><el-icon><Key /></el-icon> 已登录账号 Cookie</span>
          <el-button size="small" plain @click="reloadCookies">刷新</el-button>
        </div>
      </template>
      <el-empty v-if="!cookieStatus || cookieStatus.cookies.length === 0" :description="cookieStatus?.hint || '还没有登录账号'" />
      <el-table v-else :data="cookieStatus.cookies" stripe>
        <el-table-column label="平台" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="success">{{ cookiePlatformTag(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="账号" prop="account" min-width="160" />
        <el-table-column label="登录时间" width="180">
          <template #default="{ row }">{{ formatDate(row.modified_at) }}</template>
        </el-table-column>
        <el-table-column label="路径" min-width="280">
          <template #default="{ row }">
            <code class="path-text">{{ row.path }}</code>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 已生成视频 -->
    <el-card class="section-card" shadow="never" v-loading="loading">
      <template #header>
        <div class="flex-between">
          <span><el-icon><VideoCamera /></el-icon> 已生成视频</span>
          <el-tag size="small">{{ videos.length }} 个</el-tag>
        </div>
      </template>
      <el-empty v-if="videos.length === 0" description="还没有生成视频，去 Script Studio 创建一个项目吧" />
      <el-table v-else :data="videos" stripe>
        <el-table-column label="文件" min-width="220">
          <template #default="{ row }">
            <a :href="row.url" target="_blank" class="video-link">{{ row.filename }}</a>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
        </el-table-column>
        <el-table-column label="生成时间" width="180">
          <template #default="{ row }">{{ formatDate(row.modified_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" :icon="Promotion" @click="openPublishDialog(row)">
              Publish
            </el-button>
            <el-button size="small" plain @click="copyPath(row.path)">Copy Path</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 已发布记录 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="flex-between">
          <span><el-icon><Check /></el-icon> 已发布记录</span>
          <el-tag size="small">{{ published.length }} 个</el-tag>
        </div>
      </template>
      <el-empty v-if="published.length === 0" description="还没有发布记录" />
      <el-table v-else :data="published" stripe>
        <el-table-column label="文件" min-width="220">
          <template #default="{ row }">
            <a :href="row.url" target="_blank" class="video-link">{{ row.filename }}</a>
          </template>
        </el-table-column>
        <el-table-column label="平台" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.platform === 'local' ? 'info' : 'success'">
              {{ row.platform }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
        </el-table-column>
        <el-table-column label="发布时间" width="180">
          <template #default="{ row }">{{ formatDate(row.modified_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 发布对话框 -->
    <el-dialog v-model="publishDialogVisible" title="发布视频" width="560px">
      <el-form :model="publishForm" label-width="100px">
        <el-form-item label="视频">
          <span class="dialog-video">{{ currentVideo?.filename }}</span>
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="publishForm.platform" placeholder="选择发布平台" style="width: 100%">
            <el-option
              v-for="opt in platformOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="publishForm.platform !== 'dummy'" label="账号">
          <el-input v-model="publishForm.account" placeholder="social-auto-upload 中的账号名" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="publishForm.title" placeholder="视频标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="publishForm.description"
            type="textarea"
            :rows="3"
            placeholder="可选视频描述"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="publishForm.tags" placeholder="逗号分隔，如：效率,程序员,习惯" />
        </el-form-item>
        <el-alert
          v-if="publishForm.platform !== 'dummy' && (!supported?.sau_installed)"
          type="warning"
          :closable="false"
          title="social-auto-upload 未安装，发布会失败"
          show-icon
        />
      </el-form>
      <template #footer>
        <el-button @click="publishDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishing" :icon="UploadFilled" @click="doPublish">
          确认发布
        </el-button>
      </template>
    </el-dialog>

    <!-- 登录对话框 -->
    <el-dialog v-model="loginDialogVisible" title="扫码登录" width="500px">
      <el-alert
        class="mb-16"
        type="info"
        :closable="false"
        title="登录说明"
        description="点击确认后将启动浏览器，请在浏览器中扫码完成登录。登录成功后 cookie 会自动保存到 social-auto-upload/cookies/ 目录。"
      />
      <el-form :model="loginForm" label-width="100px">
        <el-form-item label="平台">
          <el-select v-model="loginForm.platform" style="width: 100%">
            <el-option label="抖音" value="douyin" />
            <el-option label="B 站" value="bilibili" />
            <el-option label="快手" value="kuaishou" />
            <el-option label="小红书" value="xiaohongshu" />
            <el-option label="视频号" value="tencent" />
            <el-option label="百家号" value="baijiahao" />
            <el-option label="TikTok" value="tiktok" />
            <el-option label="YouTube" value="youtube" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号名">
          <el-input v-model="loginForm.account" placeholder="给账号起个名字，便于区分多账号" />
        </el-form-item>
        <el-alert
          v-if="!supported?.sau_installed"
          type="warning"
          :closable="false"
          title="social-auto-upload 未安装，无法登录"
          show-icon
        />
      </el-form>
      <template #footer>
        <el-button @click="loginDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="logging"
          :icon="Key"
          :disabled="!supported?.sau_installed"
          @click="doLogin"
        >
          启动浏览器登录
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.platform-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.platform-class {
  margin-left: 4px;
  opacity: 0.7;
  font-size: 12px;
}

.video-link {
  color: #409eff;
  text-decoration: none;
}
.video-link:hover {
  text-decoration: underline;
}

.dialog-video {
  font-family: monospace;
  color: #606266;
  word-break: break-all;
}

.path-text {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}

.mb-16 {
  margin-bottom: 16px;
}

.flex-row {
  display: flex;
  gap: 8px;
}
</style>

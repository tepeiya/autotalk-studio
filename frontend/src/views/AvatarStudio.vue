<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import {
  avatars as avatarsApi,
  providers as providersApi,
  type AvatarProfile,
  type ProviderInfo,
} from '@/api/client'

const avatarList = ref<AvatarProfile[]>([])
const avatarProviders = ref<ProviderInfo[]>([])
const loadingList = ref(false)
const registering = ref(false)

const registerForm = reactive({
  name: '',
  provider: '',
  file: null as File | null,
})

async function loadAvatars() {
  loadingList.value = true
  try {
    avatarList.value = await avatarsApi.listAvatars()
  } catch (e: any) {
    ElMessage.error(`Failed to load avatars: ${e.message}`)
  } finally {
    loadingList.value = false
  }
}

async function loadProviders() {
  try {
    avatarProviders.value = await providersApi.listProviders('avatar')
  } catch (e: any) {
    ElMessage.warning(`Failed to load avatar providers: ${e.message}`)
  }
}

function onFileChosen(file: File) {
  registerForm.file = file
  return false
}

async function onRegister() {
  if (!registerForm.name.trim()) {
    ElMessage.warning('Please input avatar name')
    return
  }
  if (!registerForm.file) {
    ElMessage.warning('Please select a portrait image')
    return
  }
  registering.value = true
  try {
    const fd = new FormData()
    fd.append('file', registerForm.file)
    fd.append('name', registerForm.name.trim())
    if (registerForm.provider) fd.append('provider', registerForm.provider)
    const created = await avatarsApi.register(fd)
    ElMessage.success(`Avatar registered: ${created.name}`)
    registerForm.name = ''
    registerForm.provider = ''
    registerForm.file = null
    await loadAvatars()
  } catch (e: any) {
    ElMessage.error(`Register failed: ${e.message}`)
  } finally {
    registering.value = false
  }
}

function customUpload(_options: UploadRequestOptions): never {
  throw new Error('manual upload only')
}

function portraitUrl(p: AvatarProfile) {
  if (!p.portrait_path) return ''
  return `/static/${p.portrait_path.split('/').pop()}`
}

onMounted(() => {
  loadAvatars()
  loadProviders()
})
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">Avatar Studio</h2>

    <el-card class="section-card" shadow="never">
      <template #header><span>Register Avatar</span></template>
      <el-form label-width="120px">
        <el-form-item label="Avatar Name">
          <el-input v-model="registerForm.name" placeholder="Name for the avatar" clearable />
        </el-form-item>
        <el-form-item label="Avatar Provider">
          <el-select v-model="registerForm.provider" placeholder="Use default" clearable>
            <el-option
              v-for="p in avatarProviders"
              :key="p.name"
              :label="p.name"
              :value="p.name"
              :disabled="!p.available"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Portrait">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :http-request="customUpload"
            accept="image/*,video/*"
            :on-change="(file: any) => onFileChosen(file.raw)"
          >
            <el-button>Choose Image/Video</el-button>
            <template #tip>
              <div class="upload-tip">
                {{ registerForm.file ? registerForm.file.name : 'Select portrait image or video' }}
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="registering" @click="onRegister">
            Register Avatar
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="flex-between">
          <span>Registered Avatars</span>
          <el-button text :loading="loadingList" @click="loadAvatars">Refresh</el-button>
        </div>
      </template>
      <div v-loading="loadingList">
        <el-empty v-if="avatarList.length === 0" description="No avatars registered" />
        <el-row v-else :gutter="16">
          <el-col
            v-for="a in avatarList"
            :key="a.id"
            :xs="24"
            :sm="12"
            :md="8"
            :lg="6"
          >
            <el-card shadow="hover" class="avatar-card">
              <div class="avatar-preview">
                <img
                  v-if="portraitUrl(a)"
                  :src="portraitUrl(a)"
                  :alt="a.name"
                />
                <span v-else class="no-preview">No preview</span>
              </div>
              <div class="avatar-name">{{ a.name }}</div>
              <div class="avatar-meta">
                <el-tag size="small">{{ a.provider }}</el-tag>
                <span class="avatar-id">{{ a.id }}</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.avatar-card {
  margin-bottom: 16px;
}

.avatar-preview {
  width: 100%;
  aspect-ratio: 3 / 4;
  background-color: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 4px;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-preview {
  color: #c0c4cc;
  font-size: 12px;
}

.avatar-name {
  font-weight: 600;
  margin-top: 8px;
  color: #303133;
}

.avatar-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.avatar-id {
  font-size: 11px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}
</style>

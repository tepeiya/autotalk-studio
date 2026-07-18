<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import {
  media as mediaApi,
  type MediaItem,
} from '@/api/client'

const activeTab = ref<'bgm' | 'backgrounds'>('bgm')

const bgmList = ref<MediaItem[]>([])
const bgList = ref<MediaItem[]>([])
const loadingBgm = ref(false)
const loadingBg = ref(false)

const bgmUploadName = ref('')
const bgUploadName = ref('')
const bgmFile = ref<File | null>(null)
const bgFile = ref<File | null>(null)
const uploadingBgm = ref(false)
const uploadingBg = ref(false)

async function loadBgm() {
  loadingBgm.value = true
  try {
    bgmList.value = await mediaApi.listBgm()
  } catch (e: any) {
    ElMessage.error(`Failed to load BGM: ${e.message}`)
  } finally {
    loadingBgm.value = false
  }
}

async function loadBackgrounds() {
  loadingBg.value = true
  try {
    bgList.value = await mediaApi.listBackgrounds()
  } catch (e: any) {
    ElMessage.error(`Failed to load backgrounds: ${e.message}`)
  } finally {
    loadingBg.value = false
  }
}

function onBgmFile(file: File) {
  bgmFile.value = file
  if (!bgmUploadName.value) bgmUploadName.value = file.name.replace(/\.[^.]+$/, '')
  return false
}

function onBgFile(file: File) {
  bgFile.value = file
  if (!bgUploadName.value) bgUploadName.value = file.name.replace(/\.[^.]+$/, '')
  return false
}

async function uploadBgm() {
  if (!bgmFile.value) {
    ElMessage.warning('Please choose a BGM file')
    return
  }
  uploadingBgm.value = true
  try {
    const fd = new FormData()
    fd.append('file', bgmFile.value)
    if (bgmUploadName.value.trim()) fd.append('name', bgmUploadName.value.trim())
    await mediaApi.uploadBgm(fd)
    ElMessage.success('BGM uploaded')
    bgmFile.value = null
    bgmUploadName.value = ''
    await loadBgm()
  } catch (e: any) {
    ElMessage.error(`Upload failed: ${e.message}`)
  } finally {
    uploadingBgm.value = false
  }
}

async function uploadBackground() {
  if (!bgFile.value) {
    ElMessage.warning('Please choose a background image')
    return
  }
  uploadingBg.value = true
  try {
    const fd = new FormData()
    fd.append('file', bgFile.value)
    if (bgUploadName.value.trim()) fd.append('name', bgUploadName.value.trim())
    await mediaApi.uploadBackground(fd)
    ElMessage.success('Background uploaded')
    bgFile.value = null
    bgUploadName.value = ''
    await loadBackgrounds()
  } catch (e: any) {
    ElMessage.error(`Upload failed: ${e.message}`)
  } finally {
    uploadingBg.value = false
  }
}

function customUpload(_options: UploadRequestOptions): never {
  throw new Error('manual upload only')
}

function mediaUrl(item: MediaItem) {
  if (!item.path) return ''
  return `/static/${item.path.split('/').pop()}`
}

function onTabChange(name: any) {
  if (name === 'backgrounds' && bgList.value.length === 0) loadBackgrounds()
}

onMounted(() => {
  loadBgm()
  loadBackgrounds()
})
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">Media Library</h2>

    <el-card shadow="never" class="section-card">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane label="BGM" name="bgm">
          <el-card shadow="never" class="mb-16">
            <template #header><span>Upload BGM</span></template>
            <el-form label-width="120px">
              <el-form-item label="Name">
                <el-input v-model="bgmUploadName" placeholder="Optional name" clearable />
              </el-form-item>
              <el-form-item label="File">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :http-request="customUpload"
                  accept="audio/*"
                  :on-change="(file: any) => onBgmFile(file.raw)"
                >
                  <el-button>Choose Audio</el-button>
                  <template #tip>
                    <div class="upload-tip">
                      {{ bgmFile ? bgmFile.name : 'Select audio file (mp3/wav)' }}
                    </div>
                  </template>
                </el-upload>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="uploadingBgm" @click="uploadBgm">
                  Upload
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-table :data="bgmList" v-loading="loadingBgm" stripe>
            <el-table-column prop="name" label="Name" min-width="160" />
            <el-table-column prop="id" label="ID" min-width="160" />
            <el-table-column label="Preview" min-width="180">
              <template #default="{ row }">
                <audio
                  v-if="mediaUrl(row)"
                  :src="mediaUrl(row)"
                  controls
                  style="height: 28px"
                />
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="Tags" min-width="120">
              <template #default="{ row }">
                <el-tag
                  v-for="t in row.tags || []"
                  :key="t"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ t }}
                </el-tag>
                <span v-if="!row.tags || row.tags.length === 0">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="Backgrounds" name="backgrounds">
          <el-card shadow="never" class="mb-16">
            <template #header><span>Upload Background</span></template>
            <el-form label-width="120px">
              <el-form-item label="Name">
                <el-input v-model="bgUploadName" placeholder="Optional name" clearable />
              </el-form-item>
              <el-form-item label="File">
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  :http-request="customUpload"
                  accept="image/*,video/*"
                  :on-change="(file: any) => onBgFile(file.raw)"
                >
                  <el-button>Choose Image/Video</el-button>
                  <template #tip>
                    <div class="upload-tip">
                      {{ bgFile ? bgFile.name : 'Select image or video file' }}
                    </div>
                  </template>
                </el-upload>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="uploadingBg" @click="uploadBackground">
                  Upload
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <div v-loading="loadingBg">
            <el-empty v-if="bgList.length === 0" description="No backgrounds" />
            <el-row v-else :gutter="16">
              <el-col
                v-for="bg in bgList"
                :key="bg.id"
                :xs="12"
                :sm="8"
                :md="6"
              >
                <el-card shadow="hover" class="bg-card">
                  <div class="bg-preview">
                    <img v-if="mediaUrl(bg)" :src="mediaUrl(bg)" :alt="bg.name" />
                    <span v-else class="no-preview">No preview</span>
                  </div>
                  <div class="bg-name">{{ bg.name }}</div>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.bg-card {
  margin-bottom: 16px;
}

.bg-preview {
  width: 100%;
  aspect-ratio: 16 / 9;
  background-color: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 4px;
}

.bg-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-preview {
  color: #c0c4cc;
  font-size: 12px;
}

.bg-name {
  margin-top: 8px;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

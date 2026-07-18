<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  ElMessage,
  type UploadRequestOptions,
} from 'element-plus'
import {
  voices as voicesApi,
  providers as providersApi,
  type VoiceProfile,
  type ProviderInfo,
  type SynthesizeResult,
} from '@/api/client'

const voiceList = ref<VoiceProfile[]>([])
const ttsProviders = ref<ProviderInfo[]>([])
const loadingList = ref(false)
const cloning = ref(false)

const cloneForm = reactive({
  name: '',
  provider: '',
  file: null as File | null,
})

const synthForm = reactive({
  text: '',
  voice_id: '',
  provider: '',
})

const synthLoading = ref(false)
const synthResult = ref<SynthesizeResult | null>(null)
const audioRef = ref<HTMLAudioElement | null>(null)

async function loadVoices() {
  loadingList.value = true
  try {
    voiceList.value = await voicesApi.listVoices()
  } catch (e: any) {
    ElMessage.error(`Failed to load voices: ${e.message}`)
  } finally {
    loadingList.value = false
  }
}

async function loadProviders() {
  try {
    const list = await providersApi.listProviders('tts')
    ttsProviders.value = list
  } catch (e: any) {
    ElMessage.warning(`Failed to load TTS providers: ${e.message}`)
  }
}

function onCloneFile(file: File) {
  cloneForm.file = file
  return false
}

async function onCloneSubmit() {
  if (!cloneForm.name.trim()) {
    ElMessage.warning('Please input voice name')
    return
  }
  if (!cloneForm.file) {
    ElMessage.warning('Please select an audio sample')
    return
  }
  cloning.value = true
  try {
    const fd = new FormData()
    fd.append('file', cloneForm.file)
    fd.append('name', cloneForm.name.trim())
    if (cloneForm.provider) fd.append('provider', cloneForm.provider)
    const created = await voicesApi.cloneVoice(fd)
    ElMessage.success(`Voice cloned: ${created.name}`)
    cloneForm.name = ''
    cloneForm.provider = ''
    cloneForm.file = null
    await loadVoices()
  } catch (e: any) {
    ElMessage.error(`Clone failed: ${e.message}`)
  } finally {
    cloning.value = false
  }
}

async function onSynthesize() {
  if (!synthForm.text.trim()) {
    ElMessage.warning('Please input text to synthesize')
    return
  }
  if (!synthForm.voice_id) {
    ElMessage.warning('Please select a voice')
    return
  }
  synthLoading.value = true
  synthResult.value = null
  try {
    const result = await voicesApi.synthesize(
      {
        text: synthForm.text.trim(),
        voice_id: synthForm.voice_id,
      },
      synthForm.provider || undefined
    )
    synthResult.value = result
    ElMessage.success('Synthesis done')
  } catch (e: any) {
    ElMessage.error(`Synthesis failed: ${e.message}`)
  } finally {
    synthLoading.value = false
  }
}

function customUpload(_options: UploadRequestOptions): never {
  // Disable automatic upload; we handle it manually via onCloneSubmit
  throw new Error('manual upload only')
}

onMounted(() => {
  loadVoices()
  loadProviders()
})
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">Voice Lab</h2>

    <el-card class="section-card" shadow="never">
      <template #header><span>Voice Clone</span></template>
      <el-form label-width="120px">
        <el-form-item label="Voice Name">
          <el-input v-model="cloneForm.name" placeholder="Name for the cloned voice" clearable />
        </el-form-item>
        <el-form-item label="TTS Provider">
          <el-select v-model="cloneForm.provider" placeholder="Use default" clearable>
            <el-option
              v-for="p in ttsProviders"
              :key="p.name"
              :label="p.name"
              :value="p.name"
              :disabled="!p.available"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Audio Sample">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :http-request="customUpload"
            accept="audio/*"
            :on-change="(file: any) => onCloneFile(file.raw)"
          >
            <el-button>Choose Audio</el-button>
            <template #tip>
              <div class="upload-tip">
                {{ cloneForm.file ? cloneForm.file.name : 'Select a clean voice sample (wav/mp3)' }}
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="cloning" @click="onCloneSubmit">
            Clone Voice
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="flex-between">
          <span>Cloned Voices</span>
          <el-button text :loading="loadingList" @click="loadVoices">Refresh</el-button>
        </div>
      </template>
      <el-table :data="voiceList" v-loading="loadingList" stripe>
        <el-table-column prop="name" label="Name" min-width="140" />
        <el-table-column prop="provider" label="Provider" width="140" />
        <el-table-column prop="id" label="ID" min-width="180" />
        <el-table-column label="Sample" min-width="120">
          <template #default="{ row }">
            <audio
              v-if="row.sample_path"
              :src="`/static/${row.sample_path.split('/').pop()}`"
              controls
              style="height: 28px"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="Created" min-width="160">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header><span>Test Synthesis</span></template>
      <el-form label-width="120px">
        <el-form-item label="Voice">
          <el-select v-model="synthForm.voice_id" placeholder="Select a voice">
            <el-option
              v-for="v in voiceList"
              :key="v.id"
              :label="`${v.name} (${v.provider})`"
              :value="v.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Provider">
          <el-select v-model="synthForm.provider" placeholder="Use default" clearable>
            <el-option
              v-for="p in ttsProviders"
              :key="p.name"
              :label="p.name"
              :value="p.name"
              :disabled="!p.available"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Text">
          <el-input
            v-model="synthForm.text"
            type="textarea"
            :rows="3"
            placeholder="Text to synthesize"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="synthLoading" @click="onSynthesize">
            Synthesize
          </el-button>
        </el-form-item>
        <el-form-item v-if="synthResult" label="Result">
          <audio
            ref="audioRef"
            :src="synthResult.audio_url"
            controls
            style="width: 100%; max-width: 480px"
          />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>

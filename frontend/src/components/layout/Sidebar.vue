<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Document,
  Microphone,
  Avatar,
  Picture,
  List,
  Setting,
  HomeFilled,
  Promotion,
  ChatLineRound,
} from '@element-plus/icons-vue'

const emit = defineEmits<{
  (e: 'menu-click'): void
}>()

const route = useRoute()
const router = useRouter()
const activeIndex = computed(() => route.path)

const menus = [
  { index: '/', label: 'Dashboard', icon: HomeFilled },
  { index: '/script', label: 'Script Studio', icon: Document },
  { index: '/voices', label: 'Voice Lab', icon: Microphone },
  { index: '/avatars', label: 'Avatar Studio', icon: Avatar },
  { index: '/media', label: 'Media Library', icon: Picture },
  { index: '/tasks', label: 'Batch Tasks', icon: List },
  { index: '/publish', label: 'Publisher', icon: Promotion },
  { index: '/reddit', label: 'Reddit Studio', icon: ChatLineRound },
  { index: '/settings', label: 'Settings', icon: Setting },
]

function handleMenuClick(index: string) {
  if (index !== route.path) {
    router.push(index)
  }
  emit('menu-click')
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <span class="brand-text">AutoTalk</span>
      <span class="brand-sub">Studio</span>
    </div>
    <el-menu
      :default-active="activeIndex"
      :collapse="false"
      class="sidebar-menu"
      background-color="#1f2d3d"
      text-color="#c0c4cc"
      active-text-color="#ffffff"
      @select="handleMenuClick"
    >
      <el-menu-item
        v-for="m in menus"
        :key="m.index"
        :index="m.index"
      >
        <el-icon><component :is="m.icon" /></el-icon>
        <span class="menu-label">{{ m.label }}</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  background-color: #1f2d3d;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100%;
}

.sidebar-brand {
  height: 56px;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.brand-text {
  color: #ffffff;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
}

.brand-sub {
  color: #909399;
  font-size: 12px;
  line-height: 1.2;
}

.sidebar-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.sidebar-menu .el-menu-item {
  height: 46px;
  line-height: 46px;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #2c3e50;
}

.menu-label {
  margin-left: 4px;
}
</style>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import { Menu } from '@element-plus/icons-vue'

const route = useRoute()
const currentTitle = computed(() => (route.meta?.title as string) || 'AutoTalk Studio')

// 响应式宽度判断
const isMobile = ref(false)
const drawerOpen = ref(false)

function updateWidth() {
  isMobile.value = window.innerWidth <= 768
  // 切换到桌面端时自动关抽屉
  if (!isMobile.value && drawerOpen.value) {
    drawerOpen.value = false
  }
}

onMounted(() => {
  updateWidth()
  window.addEventListener('resize', updateWidth)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateWidth)
})

function openDrawer() {
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
}
</script>

<template>
  <div class="layout-wrapper">
    <!-- 桌面端：固定侧栏 -->
    <Sidebar v-if="!isMobile" />

    <!-- 移动端：抽屉式侧栏 -->
    <el-drawer
      v-if="isMobile"
      v-model="drawerOpen"
      direction="ltr"
      size="80%"
      :with-header="false"
      class="mobile-sidebar-drawer"
    >
      <Sidebar @menu-click="closeDrawer" />
    </el-drawer>

    <div class="layout-main">
      <header class="layout-header">
        <div class="header-left">
          <el-button
            v-if="isMobile"
            class="hamburger-btn"
            link
            :icon="Menu"
            size="large"
            @click="openDrawer"
          />
          <div class="header-title">{{ currentTitle }}</div>
        </div>
        <div class="header-sub">AutoTalk Studio</div>
      </header>
      <main class="layout-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout-wrapper {
  display: flex;
  height: 100vh;
  width: 100%;
}

.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.layout-header {
  height: 56px;
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.hamburger-btn {
  padding: 4px !important;
  color: #303133 !important;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-sub {
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
}

.layout-content {
  flex: 1;
  overflow: auto;
  background-color: #f5f7fa;
}

/* 抽屉内背景色匹配 sidebar */
:global(.mobile-sidebar-drawer .el-drawer__body) {
  background-color: #1f2d3d !important;
  padding: 0 !important;
}

/* ========== 平板 ≤1024px ========== */
@media (max-width: 1024px) {
  .layout-header {
    padding: 0 16px;
  }
}

/* ========== 手机 ≤768px ========== */
@media (max-width: 768px) {
  .layout-header {
    height: 52px;
    padding: 0 12px;
  }

  .header-title {
    font-size: 15px;
  }

  .header-sub {
    display: none;
  }
}

/* ========== 小屏手机 ≤480px ========== */
@media (max-width: 480px) {
  .layout-header {
    padding: 0 8px;
  }

  .header-title {
    font-size: 14px;
  }
}
</style>

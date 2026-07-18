<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'

const route = useRoute()
const currentTitle = computed(() => (route.meta?.title as string) || 'AutoTalk Studio')
</script>

<template>
  <div class="layout-wrapper">
    <Sidebar />
    <div class="layout-main">
      <header class="layout-header">
        <div class="header-title">{{ currentTitle }}</div>
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
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-sub {
  font-size: 13px;
  color: #909399;
}

.layout-content {
  flex: 1;
  overflow: auto;
  background-color: #f5f7fa;
}
</style>

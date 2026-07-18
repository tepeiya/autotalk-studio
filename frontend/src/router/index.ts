import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: 'Dashboard' },
  },
  {
    path: '/script',
    name: 'ScriptStudio',
    component: () => import('@/views/ScriptStudio.vue'),
    meta: { title: 'Script Studio' },
  },
  {
    path: '/voices',
    name: 'VoiceLab',
    component: () => import('@/views/VoiceLab.vue'),
    meta: { title: 'Voice Lab' },
  },
  {
    path: '/avatars',
    name: 'AvatarStudio',
    component: () => import('@/views/AvatarStudio.vue'),
    meta: { title: 'Avatar Studio' },
  },
  {
    path: '/media',
    name: 'MediaLibrary',
    component: () => import('@/views/MediaLibrary.vue'),
    meta: { title: 'Media Library' },
  },
  {
    path: '/tasks',
    name: 'BatchTasks',
    component: () => import('@/views/BatchTasks.vue'),
    meta: { title: 'Batch Tasks' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: 'Settings' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  const title = (to.meta?.title as string) || 'AutoTalk Studio'
  document.title = `${title} | AutoTalk Studio`
})

export default router

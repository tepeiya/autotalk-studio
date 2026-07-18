import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  projects as projectsApi,
  type Project,
  type ProjectCreatePayload,
  type TaskStatus,
} from '@/api/client'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const selected = ref<Project | null>(null)
  const loading = ref(false)

  async function fetchProjects(status?: TaskStatus | string) {
    loading.value = true
    try {
      projects.value = await projectsApi.listProjects(status)
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: string) {
    selected.value = await projectsApi.getProject(id)
    return selected.value
  }

  async function createProject(payload: ProjectCreatePayload) {
    const project = await projectsApi.createProject(payload)
    projects.value.unshift(project)
    selected.value = project
    return project
  }

  async function cancelProject(id: string) {
    await projectsApi.cancelProject(id)
    await refreshOne(id)
  }

  async function deleteProject(id: string) {
    await projectsApi.deleteProject(id)
    projects.value = projects.value.filter((p) => p.id !== id)
    if (selected.value?.id === id) selected.value = null
  }

  async function refreshOne(id: string) {
    const updated = await projectsApi.getProject(id)
    const idx = projects.value.findIndex((p) => p.id === id)
    if (idx >= 0) projects.value[idx] = updated
    if (selected.value?.id === id) selected.value = updated
    return updated
  }

  return {
    projects,
    selected,
    loading,
    fetchProjects,
    fetchProject,
    createProject,
    cancelProject,
    deleteProject,
    refreshOne,
  }
})

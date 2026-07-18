import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tasks as tasksApi, type TaskEvent } from '@/api/client'

export const useTaskStore = defineStore('task', () => {
  const events = ref<TaskEvent[]>([])
  const subscribedId = ref<string | null>(null)
  const connected = ref(false)
  let source: EventSource | null = null

  function clear() {
    events.value = []
  }

  function stop() {
    if (source) {
      source.close()
      source = null
    }
    connected.value = false
    subscribedId.value = null
  }

  async function loadHistory(id: string) {
    try {
      const history = await tasksApi.listEvents(id)
      events.value = history
    } catch {
      events.value = []
    }
  }

  function subscribe(id: string) {
    stop()
    clear()
    subscribedId.value = id
    loadHistory(id)

    source = tasksApi.streamEvents(id)

    source.onopen = () => {
      connected.value = true
    }

    source.onmessage = (ev) => {
      pushRaw(ev.data)
    }

    // 后端按 stage 名作为 SSE event 名推送，逐个监听
    const knownStages = ['script', 'voice', 'avatar', 'media', 'video', 'publish', 'done', 'error']
    for (const stage of knownStages) {
      source.addEventListener(stage, (ev: MessageEvent) => {
        pushRaw(ev.data)
      })
    }

    source.onerror = () => {
      connected.value = false
    }
  }

  function pushRaw(raw: string) {
    if (!raw) return
    try {
      const parsed = JSON.parse(raw) as TaskEvent
      events.value.push(parsed)
      // 截断过长事件流
      if (events.value.length > 500) {
        events.value = events.value.slice(-500)
      }
    } catch {
      // 忽略无法解析的消息
    }
  }

  return {
    events,
    subscribedId,
    connected,
    subscribe,
    stop,
    clear,
    loadHistory,
  }
})

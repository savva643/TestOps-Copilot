import { createApiClient } from './client'

const apiClient = createApiClient()

export async function getTaskStatus(taskId: string) {
  const response = await apiClient.get(`/api/v1/tasks/${taskId}`)
  return response.data
}

export function getTasksWebSocketUrl(taskId: string) {
  const apiBase = import.meta.env.VITE_API_URL || 'http://testops.keep-pixel.ru'
  const apiKey = import.meta.env.VITE_API_KEY || 'testops-copilot-api-key-2024'

  try {
    // Используем текущий хост страницы для WebSocket, чтобы избежать проблем с CORS и прокси
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    
    // Если API URL указывает на тот же домен, используем текущий хост
    const apiUrl = new URL(apiBase)
    const currentHost = window.location.hostname
    
    // Если домены совпадают или API URL относительный, используем текущий хост
    let wsHost = host
    if (apiUrl.hostname === currentHost || apiUrl.hostname === 'localhost' || apiUrl.hostname === '127.0.0.1') {
      wsHost = host
    } else {
      // Иначе используем хост из API URL
      wsHost = apiUrl.hostname + (apiUrl.port ? `:${apiUrl.port}` : '')
      const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = new URL(`${wsProtocol}//${wsHost}/api/v1/tasks/ws/${taskId}`)
      wsUrl.searchParams.set('api_key', apiKey)
      return wsUrl.toString()
    }
    
    const wsUrl = new URL(`${protocol}//${wsHost}/api/v1/tasks/ws/${taskId}`)
    wsUrl.searchParams.set('api_key', apiKey)
    return wsUrl.toString()
  } catch (error) {
    // Fallback если URL невалидный - используем протокол текущей страницы
    console.error('Error constructing WebSocket URL:', error)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/api/v1/tasks/ws/${taskId}?api_key=${apiKey}`
  }
}

export interface TaskListItem {
  task_id: string
  status: string
  created_at?: string
  updated_at?: string
  test_type?: string
  owner?: string
  owner_id?: string
  priority?: string
  gitlab_url?: string
  gitlab_merge_request_url?: string
  gitlab_branch?: string
  is_gitlab_task?: string
}

export interface TaskListResponse {
  items: TaskListItem[]
  total: number
  page: number
  page_size: number
}

export async function getTasks(params: { page?: number; page_size?: number; search?: string; owner_id?: string }) {
  const response = await apiClient.get<TaskListResponse>('/api/v1/tasks', { params })
  return response.data
}


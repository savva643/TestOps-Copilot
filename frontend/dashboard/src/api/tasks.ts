import { createApiClient } from './client'

const apiClient = createApiClient()

export async function getTaskStatus(taskId: string) {
  const response = await apiClient.get(`/api/v1/tasks/${taskId}`)
  return response.data
}

export function getTasksWebSocketUrl(taskId: string) {
  const base = import.meta.env.VITE_API_URL || 'https://testops.keep-pixel.ru'
  const apiKey = import.meta.env.VITE_API_KEY || 'testops-copilot-api-key-2024'
  const wsBase = base.replace(/^http/, 'ws')
  const url = new URL(`${wsBase}/api/v1/tasks/ws/${taskId}`)
  url.searchParams.set('api_key', apiKey)
  return url.toString()
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


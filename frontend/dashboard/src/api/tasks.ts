import { createApiClient } from './client'

const apiClient = createApiClient()

export async function getTaskStatus(taskId: string) {
  const response = await apiClient.get(`/api/v1/tasks/${taskId}`)
  return response.data
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


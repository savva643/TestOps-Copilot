import { createApiClient } from './client'

const apiClient = createApiClient()

export async function getTaskStatus(taskId: string) {
  const response = await apiClient.get(`/api/v1/tasks/${taskId}`)
  return response.data
}


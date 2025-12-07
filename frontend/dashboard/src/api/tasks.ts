import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || 'default-api-key-change-in-production'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': API_KEY,
  },
})

export async function getTaskStatus(taskId: string) {
  const response = await apiClient.get(`/api/v1/tasks/${taskId}`)
  return response.data
}


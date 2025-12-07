import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || 'default-api-key-change-in-production'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
  },
})

export interface GenerateTestCaseRequest {
  description: string
  test_type?: string
  feature?: string
  story?: string
  priority?: string
  owner?: string
  jira_link?: string
}

export async function generateTestCase(request: GenerateTestCaseRequest) {
  const response = await apiClient.post('/api/v1/generate/test-case', request)
  return response.data
}


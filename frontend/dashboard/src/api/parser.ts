import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || 'testops-copilot-api-key-2024'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': API_KEY,
  },
})

export interface ParseOpenAPIResponse {
  endpoints: Array<{
    path: string
    method: string
    operation_id?: string
    summary?: string
    description?: string
  }>
  schemas: Record<string, any>
  info: {
    title?: string
    version?: string
    description?: string
    [key: string]: any
  }
}

export async function parseOpenAPI(file: File): Promise<ParseOpenAPIResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<ParseOpenAPIResponse>(
    '/api/v1/parse/openapi',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}


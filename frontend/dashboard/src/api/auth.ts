import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || 'testops-copilot-api-key-2024'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': API_KEY,
  },
})

export interface TokenResponse {
  access_token: string
  expires_in?: number
  token_type?: string
  [key: string]: any
}

export async function fetchIamToken(keyId: string, secret: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/api/v1/auth/token', { keyId, secret })
  return response.data
}


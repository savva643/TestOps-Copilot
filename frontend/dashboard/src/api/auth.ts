import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || 'testops-copilot-api-key-2024'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
  },
})

export interface TokenResponse {
  access_token: string
  expires_in?: number
  token_type?: string
  [key: string]: any
}

const TOKEN_KEY = 'copilot_access_token'
const KEY_ID_KEY = 'copilot_key_id'
const SECRET_KEY = 'copilot_secret'
const LLM_API_KEY_KEY = 'copilot_llm_api_key'

export function getStoredCredentials(): { keyId: string; secret: string; llmApiKey?: string } | null {
  const keyId = localStorage.getItem(KEY_ID_KEY)
  const secret = localStorage.getItem(SECRET_KEY)
  const llmApiKey = localStorage.getItem(LLM_API_KEY_KEY)
  if (keyId && secret) {
    return { keyId, secret, llmApiKey: llmApiKey || undefined }
  }
  return null
}

export function storeCredentials(keyId: string, secret: string, llmApiKey?: string) {
  localStorage.setItem(KEY_ID_KEY, keyId)
  localStorage.setItem(SECRET_KEY, secret)
  if (llmApiKey) {
    localStorage.setItem(LLM_API_KEY_KEY, llmApiKey)
  }
}

export function getStoredLlmApiKey(): string | null {
  return localStorage.getItem(LLM_API_KEY_KEY)
}

export function clearCredentials() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(KEY_ID_KEY)
  localStorage.removeItem(SECRET_KEY)
  localStorage.removeItem(LLM_API_KEY_KEY)
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function storeToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

let tokenRefreshPromise: Promise<string> | null = null

export async function refreshToken(): Promise<string> {
  if (tokenRefreshPromise) {
    return tokenRefreshPromise
  }

  const credentials = getStoredCredentials()
  if (!credentials) {
    throw new Error('No credentials stored')
  }

  tokenRefreshPromise = (async () => {
    try {
      const response = await apiClient.post<TokenResponse>('/api/v1/auth/token', {
        keyId: credentials.keyId,
        secret: credentials.secret,
      })
      const token = response.data.access_token
      if (token) {
        storeToken(token)
        return token
      }
      throw new Error('No token in response')
    } finally {
      tokenRefreshPromise = null
    }
  })()

  return tokenRefreshPromise
}

export async function getValidToken(): Promise<string | null> {
  const stored = getStoredToken()
  if (stored) {
    return stored
  }

  const credentials = getStoredCredentials()
  if (credentials) {
    try {
      return await refreshToken()
    } catch {
      return null
    }
  }

  return null
}

export async function fetchIamToken(keyId: string, secret: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/api/v1/auth/token', { keyId, secret })
  return response.data
}

// Interceptor для автоматического обновления токена при 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const newToken = await refreshToken()
        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return apiClient(originalRequest)
        }
      } catch {
        clearCredentials()
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

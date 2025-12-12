import axios, { AxiosInstance } from 'axios'
import { getValidToken, getStoredLlmApiKey } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://testops.keep-pixel.ru'
const API_KEY = import.meta.env.VITE_API_KEY || 'testops-copilot-api-key-2024'

export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_URL,
    headers: {
      'X-API-Key': API_KEY,
    },
  })

  // Interceptor для добавления токена и LLM API ключа к каждому запросу
  client.interceptors.request.use(
    async (config) => {
      const token = await getValidToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      const credentials = await import('./auth').then((mod) => mod.getStoredCredentials())
      if (credentials?.keyId) {
        config.headers['X-Key-Id'] = credentials.keyId
      }
      const llmApiKey = getStoredLlmApiKey()
      if (llmApiKey) {
        config.headers['X-LLM-API-Key'] = llmApiKey
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Interceptor для автоматического обновления токена при 401
  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config

      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true

        try {
          const { refreshToken } = await import('./auth')
          const newToken = await refreshToken()
          if (newToken) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return client(originalRequest)
          }
        } catch {
          const { clearCredentials } = await import('./auth')
          clearCredentials()
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }
      }

      return Promise.reject(error)
    }
  )

  return client
}


import { createApiClient } from './client'
import { getStoredLlmApiKey } from './auth'

const apiClient = createApiClient()

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  messages: ChatMessage[]
  temperature?: number
  max_tokens?: number
  session_id?: string
  owner_id?: string
}

export interface ChatResponse {
  content: string
  model: string
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
  context_tokens: number
  context_full: boolean
  context_percentage: number
}

export interface ContextInfo {
  max_context_tokens: number
  recommended_max_request_tokens: number
  warning_threshold_percentage: number
  model: string
  description: string
}

/**
 * Send a chat message to GigaChat via backend API.
 * 
 * @param messages - List of chat messages (conversation history)
 * @param options - Optional parameters (temperature, max_tokens)
 * @returns Chat response with content and context information
 */
export async function sendChatMessage(
  messages: ChatMessage[],
  options?: {
    maxTokens?: number
    temperature?: number
    sessionId?: string
    ownerId?: string
  }
): Promise<ChatResponse> {
  const llmApiKey = getStoredLlmApiKey()
  if (!llmApiKey) {
    throw new Error('GigaChat API ключ не найден. Пожалуйста, введите API ключ при входе.')
  }

  const response = await apiClient.post<ChatResponse>('/api/v1/gigachat/chat', {
    messages: messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    })),
    temperature: options?.temperature || 0.5,
    max_tokens: options?.maxTokens || 4000,
    session_id: options?.sessionId,
    owner_id: options?.ownerId,
  }, {
    headers: {
      'X-LLM-API-Key': llmApiKey,
    },
  })

  return response.data
}

/**
 * Get context information (limits, thresholds, etc.)
 */
export async function getContextInfo(): Promise<ContextInfo> {
  const response = await apiClient.get<ContextInfo>('/api/v1/gigachat/context-info')
  return response.data
}

/**
 * Check if GigaChat is available (API key exists)
 */
export function isGigaChatAvailable(): boolean {
  return !!getStoredLlmApiKey()
}

/**
 * Compress chat history for a session
 */
export async function compressChat(sessionId: string): Promise<{
  session_id: string
  compressed_context: string
  compressed_at: string
  original_messages: number
}> {
  const llmApiKey = getStoredLlmApiKey()
  if (!llmApiKey) {
    throw new Error('GigaChat API ключ не найден.')
  }

  const response = await apiClient.post(
    `/api/v1/gigachat/chat/${sessionId}/compress`,
    {},
    {
      headers: {
        'X-LLM-API-Key': llmApiKey,
      },
    }
  )

  return response.data
}

/**
 * Get compressed memory (context) for a chat session
 */
export async function getChatMemory(sessionId: string): Promise<{
  session_id: string
  compressed_context: string
  compressed_at: string | null
  total_messages: number
  total_tokens: number
}> {
  const response = await apiClient.get(`/api/v1/gigachat/chat/${sessionId}/memory`)
  return response.data
}

/**
 * Generate a unique session ID
 */
export function generateSessionId(): string {
  return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Clear chat session on backend (delete history from DB)
 */
export async function clearChatSession(sessionId: string): Promise<{
  session_id: string
  status: string
}> {
  const response = await apiClient.delete(`/api/v1/gigachat/chat/${sessionId}`)
  return response.data
}
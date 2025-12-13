import OpenAI from 'openai'
import { getStoredLlmApiKey } from './auth'

const GIGACHAT_BASE_URL = 'https://foundation-models.api.cloud.ru/v1'
// Используем GigaChat3 - бесплатная модель с большим контекстом (262к токенов)
// и поддержкой Function Calling и Structured Output
const GIGACHAT_MODEL = 'GigaChat/GigaChat3-10B-A1.8B'

// Системный промпт для GigaChat
const SYSTEM_PROMPT = `Ты — специализированный помощник для QA-разработчиков в сервисе автоматической генерации тестов.

ТВОЯ РОЛЬ:
1. Помогать создавать тесты трёх типов:
   - РУЧНЫЕ ТЕСТЫ: подробное описание шагов в формате Markdown (\`.md\`)
   - API-ТЕСТЫ: код на Python (\`.py\`) с использованием библиотеки requests + пояснение в \`.md\`
   - UI-ТЕСТЫ: код на Python (\`.py\`) с использованием selenium/playwright + пояснение в \`.md\`

2. Ты получаешь:
   - Исходный код приложения (Python, JavaScript, etc.)
   - Описание функциональности или требования
   - Файлы проекта для анализа
   - Конкретный запрос пользователя (например: "создай API-тест для эндпоинта /login")

3. Ты анализируешь материалы и генерируешь:
   - Чистый, готовый к запуску код на Python
   - Документацию в формате Markdown
   - Примеры использования
   - Обработку ошибок

ФОРМАТ ОТВЕТА:
- Для кода используй блоки \`\`\`python ... \`\`\`
- Для документации используй Markdown
- Если нужно несколько файлов, разделяй их заголовками ### Файл: filename.py

ПРАВИЛА:
1. Следуй best practices тестирования
2. Добавляй комментарии в код
3. Учитывай контекст проекта
4. Задавай уточняющие вопросы, если информации недостаточно
5. Помни контекст предыдущих сообщений в разговоре`

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface ChatCompletionResponse {
  content: string
  model: string
  usage?: {
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
}

let gigachatClient: OpenAI | null = null
let currentApiKey: string | null = null

function getGigaChatClient(): OpenAI {
  const apiKey = getStoredLlmApiKey()
  if (!apiKey) {
    throw new Error('GigaChat API ключ не найден. Пожалуйста, введите API ключ при входе.')
  }

  // Пересоздаем клиент, если ключ изменился
  if (!gigachatClient || currentApiKey !== apiKey) {
    gigachatClient = new OpenAI({
      apiKey: apiKey,
      baseURL: GIGACHAT_BASE_URL,
    })
    currentApiKey = apiKey
  }

  return gigachatClient
}

export async function sendChatMessage(
  messages: ChatMessage[],
  options?: {
    maxTokens?: number
    temperature?: number
  }
): Promise<ChatCompletionResponse> {
  try {
    const client = getGigaChatClient()

    // Добавляем системный промпт, если его еще нет
    const messagesWithSystem = messages.some((m) => m.role === 'system')
      ? messages
      : [{ role: 'system' as const, content: SYSTEM_PROMPT }, ...messages]

    const response = await client.chat.completions.create({
      model: GIGACHAT_MODEL,
      messages: messagesWithSystem.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
      // GigaChat3 поддерживает больший контекст (262к токенов), можно увеличить max_tokens
      max_tokens: options?.maxTokens || 4000,
      temperature: options?.temperature || 0.5,
      presence_penalty: 0,
      top_p: 0.95,
    })

    return {
      content: response.choices[0].message.content || '',
      model: response.model,
      usage: response.usage
        ? {
            prompt_tokens: response.usage.prompt_tokens,
            completion_tokens: response.usage.completion_tokens,
            total_tokens: response.usage.total_tokens,
          }
        : undefined,
    }
  } catch (error: any) {
    if (error.message?.includes('API ключ')) {
      throw error
    }
    
    // Обработка ошибок OpenAI SDK
    if (error.status === 401 || error.statusCode === 401) {
      resetGigaChatClient()
      throw new Error('Неверный API ключ GigaChat. Проверьте ключ в настройках.')
    }
    
    if (error.status === 429 || error.statusCode === 429) {
      throw new Error('Превышен лимит запросов. Попробуйте позже.')
    }
    
    if (error.status === 500 || error.statusCode === 500) {
      throw new Error('Ошибка сервера GigaChat. Попробуйте позже.')
    }

    // Обработка ошибок от OpenAI SDK
    const errorMessage = error.message || error.error?.message || 'Ошибка при обращении к GigaChat API'
    throw new Error(errorMessage)
  }
}

// Функция для проверки доступности API ключа
export function isGigaChatAvailable(): boolean {
  return !!getStoredLlmApiKey()
}

// Сброс клиента при смене ключа
export function resetGigaChatClient() {
  gigachatClient = null
  currentApiKey = null
}


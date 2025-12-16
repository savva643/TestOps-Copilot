import { useState, useRef, useEffect, useMemo } from 'react'
import { MdMoreVert, MdSend, MdDeleteOutline, MdInfoOutline, MdMemory } from 'react-icons/md'
import { Alert } from '@snack-uikit/alert'
import { ButtonFilled } from '@snack-uikit/button'
import {
  sendChatMessage,
  isGigaChatAvailable,
  generateSessionId,
  getChatMemory,
  compressChat,
  clearChatSession,
  type ChatMessage,
} from '../api/gigachat'
import { getStoredCredentials } from '../api/auth'
import './GigachatPage.css'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

// Полный список примеров запросов
const ALL_EXAMPLE_PROMPTS = [
  'Создай ручной тест для функции регистрации пользователя',
  'Проанализируй код и создай UI-тесты для страницы логина',
  'Сгенерируй API-тест для REST эндпоинта POST /api/users',
  'Создай полный набор тестов (ручные + API + UI) для корзины покупок',
  'Напиши тест для проверки валидации email при регистрации',
  'Создай API-тест для эндпоинта авторизации с проверкой токена',
  'Сгенерируй UI-тест для формы обратной связи',
  'Напиши ручной тест для процесса восстановления пароля',
  'Создай тест для проверки работы корзины покупок',
  'Сгенерируй API-тест для CRUD операций с пользователями',
  'Напиши UI-тест для страницы профиля пользователя',
  'Создай тест для проверки фильтрации товаров',
  'Сгенерируй интеграционный тест для процесса оплаты',
  'Напиши тест для проверки работы поиска',
  'Создай API-тест для загрузки файлов',
  'Сгенерируй UI-тест для модального окна',
  'Напиши тест для проверки работы пагинации',
  'Создай тест для валидации формы с множеством полей',
  'Сгенерируй API-тест для работы с WebSocket',
  'Напиши тест для проверки работы уведомлений',
]

// Функция для получения случайных 4 примеров
function getRandomExamples(count: number = 4): string[] {
  const shuffled = [...ALL_EXAMPLE_PROMPTS].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
}

export function GigachatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showMenu, setShowMenu] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [, setContextTokens] = useState(0)
  const [contextPercentage, setContextPercentage] = useState(0)
  const [contextFull, setContextFull] = useState(false)
  const [sessionId, setSessionId] = useState(() => generateSessionId())
  const [showMemoryModal, setShowMemoryModal] = useState(false)
  const [memoryContent, setMemoryContent] = useState<string | null>(null)
  const [loadingMemory, setLoadingMemory] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  // Получаем случайные примеры при монтировании компонента
  const examplePrompts = useMemo(() => getRandomExamples(4), [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Закрытие меню при клике вне его
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false)
      }
    }

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showMenu])

  // Проверка доступности API ключа
  const apiKeyAvailable = isGigaChatAvailable()

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    // Проверяем наличие API ключа
    if (!apiKeyAvailable) {
      setError('GigaChat API ключ не найден. Пожалуйста, введите API ключ при входе в систему.')
      return
    }

    // Проверяем, не переполнен ли контекст
    if (contextFull) {
      setError('Контекст чата переполнен. Пожалуйста, очистите чат перед отправкой нового сообщения.')
      return
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    try {
      // Формируем историю сообщений для контекста
      const chatHistory: ChatMessage[] = messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      // Добавляем текущее сообщение пользователя
      chatHistory.push({
        role: 'user',
        content: userMessage.content,
      })

      // Получаем owner_id из credentials
      const credentials = getStoredCredentials()
      const ownerId = credentials?.keyId || undefined

      // Отправляем запрос в GigaChat с session_id
      const response = await sendChatMessage(chatHistory, {
        maxTokens: 4000,
        temperature: 0.5,
        sessionId: sessionId,
        ownerId: ownerId,
      })

      // Обновляем информацию о контексте
      setContextTokens(response.context_tokens)
      setContextPercentage(response.context_percentage)
      setContextFull(response.context_full)

      // Автоматически сжимаем, если контекст переполнен
      if (response.context_full && !memoryContent) {
        // Сжимаем в фоне (не блокируем UI)
        compressChat(sessionId).catch((err) => {
          console.warn('Failed to auto-compress chat:', err)
        })
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err: any) {
      const errorMessage =
        err.message || 'Произошла ошибка при обращении к GigaChat. Попробуйте позже.'
      setError(errorMessage)

      // Добавляем сообщение об ошибке в чат
      const errorChatMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ Ошибка: ${errorMessage}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorChatMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleExampleClick = (example: string) => {
    setInputValue(example)
    // Фокусируемся на поле ввода
    setTimeout(() => {
      const textarea = document.querySelector('.gigachat-input') as HTMLTextAreaElement
      textarea?.focus()
    }, 100)
  }

  const handleClearChat = async () => {
    setMessages([])
    setShowMenu(false)
    setError(null)
    setContextTokens(0)
    setContextPercentage(0)
    setContextFull(false)
    setMemoryContent(null)

    // Пытаемся очистить историю на бэкенде, но не блокируем UI при ошибке
    try {
      if (sessionId) {
        await clearChatSession(sessionId)
      }
    } catch (err) {
      console.warn('Failed to clear chat session on backend', err)
    } finally {
      // Начинаем новую сессию, чтобы дальнейшие сообщения шли в чистый контекст
      setSessionId(generateSessionId())
    }
  }

  const handleShowMemory = async () => {
    setShowMenu(false)
    setShowMemoryModal(true)
    setLoadingMemory(true)

    try {
      // Сначала пытаемся получить память
      const memory = await getChatMemory(sessionId)
      setMemoryContent(memory.compressed_context || 'Память еще не сжата.')
    } catch (err: any) {
      // Если памяти нет, пытаемся сжать
      try {
        await compressChat(sessionId)
        const memory = await getChatMemory(sessionId)
        setMemoryContent(memory.compressed_context || 'Память еще не сжата.')
      } catch (compressErr: any) {
        setMemoryContent('Ошибка при загрузке памяти: ' + (compressErr.message || 'Неизвестная ошибка'))
      }
    } finally {
      setLoadingMemory(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Автоматическое изменение высоты textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value)
    // Автоматическое изменение высоты
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
  }

  const isEmpty = messages.length === 0

  return (
    <div className="gigachat-page">
      <div className="gigachat-chat-container">
        {/* Хедер чата */}
        <div className="gigachat-header">
          <div className="gigachat-header-left">
            <img
              src="/gigachat_green_logo.png"
              alt="GigaChat"
              className="gigachat-header-logo"
              onError={(e) => {
                const target = e.target as HTMLImageElement
                target.style.display = 'none'
              }}
            />
            <h2 className="gigachat-header-title">GigaChat</h2>
            {!isEmpty && (
              <div className="gigachat-context-progress">
                <div className="gigachat-context-progress-bar">
                  <div
                    className={`gigachat-context-progress-fill ${
                      contextFull ? 'context-full' : contextPercentage > 80 ? 'context-warning' : ''
                    }`}
                    style={{ width: `${Math.min(contextPercentage, 100)}%` }}
                  />
                </div>
                <span className="gigachat-context-percentage">
                  {contextPercentage.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
          <div className="gigachat-header-right">
            <div className="gigachat-menu-container" ref={menuRef}>
              <button
                className="gigachat-menu-button"
                onClick={() => setShowMenu(!showMenu)}
                aria-label="Меню"
              >
                <MdMoreVert className="gigachat-menu-icon" />
              </button>
              {showMenu && (
                <div className="gigachat-menu-dropdown">
                  <button
                    className="gigachat-menu-item"
                    onClick={handleClearChat}
                    disabled={isEmpty}
                  >
                    <MdDeleteOutline className="gigachat-menu-item-icon" />
                    <span>Очистить чат</span>
                  </button>
                  <button
                    className="gigachat-menu-item"
                    onClick={handleShowMemory}
                    disabled={isEmpty}
                  >
                    <MdMemory className="gigachat-menu-item-icon" />
                    <span>Показать память GigaChat</span>
                  </button>
                  <a
                    href="https://cloud.ru/products/gigachat"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="gigachat-menu-item"
                    onClick={() => setShowMenu(false)}
                  >
                    <MdInfoOutline className="gigachat-menu-item-icon" />
                    <span>О GigaChat</span>
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Область сообщений */}
        <div className="gigachat-messages-container">
          {!apiKeyAvailable && (
            <div className="gigachat-error-container">
              <Alert
                appearance="error"
                title="API ключ не найден"
                description="Для использования GigaChat необходимо ввести API ключ при входе в систему. Пожалуйста, перейдите в профиль и добавьте ключ."
              />
            </div>
          )}

          {error && apiKeyAvailable && (
            <div className="gigachat-error-container">
              <Alert appearance="error" title="Ошибка" description={error} />
            </div>
          )}

          {contextFull && !isEmpty && (
            <div className="gigachat-error-container">
              <Alert
                appearance="warning"
                title="Контекст переполнен"
                description={
                  <div>
                    <p>
                      Контекст чата заполнен на {contextPercentage.toFixed(1)}%. 
                      Для продолжения разговора необходимо очистить чат.
                    </p>
                    <button
                      className="gigachat-clear-context-button"
                      onClick={handleClearChat}
                    >
                      Очистить чат
                    </button>
                  </div>
                }
              />
            </div>
          )}

          {isEmpty ? (
            <div className="gigachat-empty-state">
              <div className="gigachat-empty-logo">
                <img
                  src="/gigachat_green_logo.png"
                  alt="GigaChat"
                  className="gigachat-empty-logo-img"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.style.display = 'none'
                  }}
                />
              </div>
              <h3 className="gigachat-empty-title">GigaChat</h3>
              <p className="gigachat-empty-subtitle">
                Помощник для генерации тестов и анализа кода
              </p>
              {apiKeyAvailable && (
                <div className="gigachat-examples">
                  <p className="gigachat-examples-title">Примеры запросов:</p>
                  <div className="gigachat-examples-list">
                    {examplePrompts.map((example, index) => (
                      <button
                        key={index}
                        className="gigachat-example-item"
                        onClick={() => handleExampleClick(example)}
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="gigachat-messages">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`gigachat-message gigachat-message-${message.role}`}
                >
                  <div className="gigachat-message-content">
                    {message.role === 'assistant' && (
                      <div className="gigachat-message-avatar">
                        <img
                          src="/gigachat_green_logo.png"
                          alt="GigaChat"
                          className="gigachat-message-avatar-img"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement
                            target.style.display = 'none'
                          }}
                        />
                      </div>
                    )}
                    <div className="gigachat-message-text">
                      <div className="gigachat-message-text-content">
                        {message.content.split('\n').map((line, i) => (
                          <span key={i}>
                            {line}
                            {i < message.content.split('\n').length - 1 && <br />}
                          </span>
                        ))}
                      </div>
                      <div className="gigachat-message-time">
                        {message.timestamp.toLocaleTimeString('ru-RU', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="gigachat-message gigachat-message-assistant">
                  <div className="gigachat-message-content">
                    <div className="gigachat-message-avatar">
                      <img
                        src="/gigachat_green_logo.png"
                        alt="GigaChat"
                        className="gigachat-message-avatar-img"
                        onError={(e) => {
                          const target = e.target as HTMLImageElement
                          target.style.display = 'none'
                        }}
                      />
                    </div>
                    <div className="gigachat-message-text">
                      <div className="gigachat-typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Поле ввода */}
        <div className="gigachat-input-container">
          <div className="gigachat-input-wrapper">
            <textarea
              className="gigachat-input"
              placeholder={
                apiKeyAvailable
                  ? 'Введите ваш запрос...'
                  : 'Для использования GigaChat введите API ключ в настройках профиля'
              }
              value={inputValue}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              rows={1}
              disabled={isLoading || !apiKeyAvailable}
            />
            <button
              className="gigachat-send-button"
              onClick={handleSendMessage}
              disabled={
                !inputValue.trim() || isLoading || !apiKeyAvailable || contextFull
              }
              aria-label="Отправить сообщение"
              title={contextFull ? 'Контекст переполнен. Очистите чат.' : ''}
            >
              <MdSend className="gigachat-send-icon" />
            </button>
          </div>
        </div>
      </div>

      {/* Модальное окно памяти GigaChat */}
      {showMemoryModal && (
        <div className="gigachat-memory-modal-overlay" onClick={() => setShowMemoryModal(false)}>
          <div className="gigachat-memory-modal" onClick={(e) => e.stopPropagation()}>
            <div className="gigachat-memory-modal-header">
              <h3>Память GigaChat</h3>
              <button
                className="gigachat-memory-modal-close"
                onClick={() => setShowMemoryModal(false)}
                aria-label="Закрыть"
              >
                ×
              </button>
            </div>
            <div className="gigachat-memory-modal-content">
              {loadingMemory ? (
                <div className="gigachat-memory-loading">Загрузка памяти...</div>
              ) : (
                <div className="gigachat-memory-text">
                  {memoryContent || 'Память еще не сжата. Используйте функцию сжатия для оптимизации контекста.'}
                </div>
              )}
            </div>
            <div className="gigachat-memory-modal-footer">
              <ButtonFilled
                label="Закрыть"
                onClick={() => setShowMemoryModal(false)}
                appearance="neutral"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

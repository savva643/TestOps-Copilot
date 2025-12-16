import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert } from '@snack-uikit/alert'
import { ButtonFilled } from '@snack-uikit/button'
import { Card } from '@snack-uikit/card'
import { Status } from '@snack-uikit/status'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getTaskStatus, getTasksWebSocketUrl, getTaskArtifacts, type TaskFileArtifact } from '../api/tasks'
import { generateTestCase } from '../api/testGeneration'
import './TasksPage.css'

interface TestFile {
  description: string | null
  code: string
  filename: string
}

interface TaskStatus {
  task_id: string
  status: string
  result?: any
  updated_at?: string
  created_at?: string
  error?: string
  progress?: {
    current: number
    total: number
    message: string
  }
}

export function TaskDetailsPage() {
  const { taskId = '' } = useParams()
  const navigate = useNavigate()
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [artifacts, setArtifacts] = useState<TestFile[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [progressVisible, setProgressVisible] = useState(true)
  const [progressFading, setProgressFading] = useState(false)
  const [recreating, setRecreating] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const usePollingRef = useRef(false)

  const isTerminal = (status?: string) => {
    if (!status) return false
    const s = status.toUpperCase()
    // Только явно завершенные статусы считаются терминальными
    return s === 'SUCCESS' || s === 'COMPLETED' || s === 'FAILURE' || s === 'FAILED'
  }

  const getStatusAppearance = (status: string): 'green' | 'red' | 'yellow' | 'neutral' => {
    const statusUpper = status.toUpperCase()
    switch (statusUpper) {
      case 'SUCCESS':
      case 'COMPLETED':
        return 'green'
      case 'FAILURE':
      case 'FAILED':
        return 'red'
      case 'PENDING':
      case 'PROGRESS':
      case 'IN_PROGRESS':
        return 'yellow'
      default:
        return 'neutral'
    }
  }

  const getStatusLabel = (status: string): string => {
    const statusUpper = status.toUpperCase()
    switch (statusUpper) {
      case 'SUCCESS':
      case 'COMPLETED':
        return 'Завершено'
      case 'FAILURE':
      case 'FAILED':
        return 'Ошибка'
      case 'PENDING':
        return 'Ожидание'
      case 'PROGRESS':
      case 'IN_PROGRESS':
        return 'В процессе'
      default:
        return status
    }
  }

  const startPolling = () => {
    if (!taskId || usePollingRef.current) return
    
    usePollingRef.current = true
    const poll = async () => {
      if (!taskId) return
      try {
        const status = await getTaskStatus(taskId)
        setTaskStatus(status)
        setError(null)
        if (!isTerminal(status.status)) {
          pollingRef.current = setTimeout(poll, 2000) // Poll every 2 seconds
        } else {
          pollingRef.current = null
        }
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || err.message || 'Не удалось получить статус задачи'
        setError(errorMsg)
        // Continue polling even on error
        pollingRef.current = setTimeout(poll, 5000) // Retry after 5 seconds on error
      }
    }
    poll()
  }

  const stopPolling = () => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)
      pollingRef.current = null
    }
    usePollingRef.current = false
  }

  const connectWebSocket = () => {
    if (!taskId || usePollingRef.current) return
    setConnecting(true)
    const url = getTasksWebSocketUrl(taskId)
    
    let wsTimeout: ReturnType<typeof setTimeout> | null = null
    
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      // Timeout для подключения - если не подключился за 5 секунд, переключаемся на polling
      wsTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.warn('WebSocket connection timeout, switching to polling')
          ws.close()
          setConnecting(false)
          setError('WebSocket недоступен, используем опрос статуса.')
          startPolling()
        }
      }, 5000)

      ws.onopen = () => {
        if (wsTimeout) {
          clearTimeout(wsTimeout)
          wsTimeout = null
        }
        setConnecting(false)
        setError(null)
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // Не обновляем статус если задача уже завершена (защита от устаревших данных)
          setTaskStatus((currentStatus) => {
            // Если текущий статус уже завершен, не перезаписываем его
            if (currentStatus && isTerminal(currentStatus.status)) {
              console.log('Ignoring WebSocket update - task already completed', {
                current: currentStatus.status,
                received: data.status
              })
              return currentStatus
            }
            
            // Проверяем updated_at чтобы не перезаписывать новыми данными старыми
            if (currentStatus && currentStatus.updated_at && data.updated_at) {
              const currentTime = new Date(currentStatus.updated_at).getTime()
              const receivedTime = new Date(data.updated_at).getTime()
              if (receivedTime < currentTime) {
                console.log('Ignoring WebSocket update - received older data', {
                  current: currentStatus.updated_at,
                  received: data.updated_at
                })
                return currentStatus
              }
            }
            
            return data
          })
          
          setError(null)
          if (isTerminal(data.status)) {
            ws.close()
          }
        } catch (err) {
          console.error('WS parse error', err)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        if (wsTimeout) {
          clearTimeout(wsTimeout)
          wsTimeout = null
        }
        setConnecting(false)
        // Не показываем ошибку сразу, попробуем polling
        setError(null)
        ws.close()
      }

      ws.onclose = (event) => {
        if (wsTimeout) {
          clearTimeout(wsTimeout)
          wsTimeout = null
        }
        wsRef.current = null
        
        // Если закрылось с ошибкой и мы еще не используем polling, переключаемся
        if (event.code !== 1000 && !usePollingRef.current) {
          console.warn('WebSocket closed unexpectedly, switching to polling', event.code, event.reason)
          setError('WebSocket недоступен, используем опрос статуса.')
          startPolling()
        }
      }
    } catch (err: any) {
      if (wsTimeout) {
        clearTimeout(wsTimeout)
      }
      setConnecting(false)
      console.error('Failed to create WebSocket:', err)
      setError('Не удалось создать WebSocket соединение, используем опрос.')
      startPolling()
    }
  }

  const fetchOnce = async (): Promise<boolean> => {
    if (!taskId) return false
    try {
      console.log('Fetching initial task status from DB...', taskId)
      const status = await getTaskStatus(taskId)
      console.log('Initial status loaded:', status.status, status.updated_at)
      setTaskStatus(status)
      setError(null)
      // Возвращаем true если задача уже завершена
      const completed = isTerminal(status.status)
      if (completed) {
        console.log('Task is already completed, will not connect WebSocket')
      }
      return completed
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Не удалось получить статус задачи'
      console.error('Failed to fetch initial status:', errorMsg)
      setError(errorMsg)
      return false
    }
  }

  useEffect(() => {
    // Сначала загружаем актуальный статус из БД через HTTP
    const loadInitialStatus = async () => {
      const isCompleted = await fetchOnce()
      // Небольшая задержка чтобы HTTP запрос точно завершился перед WebSocket
      await new Promise(resolve => setTimeout(resolve, 100))
      // Только если задача не завершена, подключаем WebSocket для обновлений
      if (!isCompleted) {
        connectWebSocket()
      } else {
        console.log('Task already completed, skipping WebSocket connection')
      }
    }
    
    loadInitialStatus()

    // Отдельно грузим артефакты из БД, чтобы тесты были доступны даже без Celery
    const loadArtifacts = async () => {
      if (!taskId) return
      try {
        const data = await getTaskArtifacts(taskId)
        if (data.files && data.files.length > 0) {
          const files: TestFile[] = data.files.map((file: TaskFileArtifact) => ({
            filename: file.filename,
            code: file.content,
            description: file.description ?? null,
          }))
          setArtifacts(files)
        } else {
          setArtifacts(null)
        }
      } catch (err) {
        // Тихо игнорируем отсутствие артефактов, чтобы не ломать старый поток
        setArtifacts(null)
      }
    }

    loadArtifacts()
    
    return () => {
      wsRef.current?.close()
      stopPolling()
    }
  }, [taskId])

  // Smoothly hide progress widget when задача завершается
  useEffect(() => {
    if (isTerminal(taskStatus?.status)) {
      setProgressFading(true)
      const timer = setTimeout(() => setProgressVisible(false), 600)
      return () => clearTimeout(timer)
    } else {
      setProgressVisible(true)
      setProgressFading(false)
    }
  }, [taskStatus?.status])

  // Проверяет, является ли файл markdown файлом
  const isMarkdownFile = (filename: string): boolean => {
    const lower = filename.toLowerCase()
    return lower.endsWith('.md') || lower.endsWith('.markdown') || 
           lower === 'explanation.md' ||
           (lower.endsWith('.txt') && taskStatus?.result?.test_type?.toLowerCase() === 'manual')
  }

  // Получаем структуру файлов из результата
  const getTestFiles = (): TestFile[] => {
    // Сначала пробуем взять артефакты из БД
    if (artifacts && artifacts.length > 0) {
      return artifacts
    }

    if (!taskStatus?.result?.test_case) return []
    
    const testCase = taskStatus.result.test_case
    
    // Если это новая структура с файлами
    if (typeof testCase === 'object' && testCase.files && Array.isArray(testCase.files)) {
      return testCase.files as TestFile[]
    }
    
    // Если это старая структура (строка) - преобразуем
    if (typeof testCase === 'string') {
      // Для ручных тестов это markdown, для других - код
      const isManual = taskStatus?.result?.test_type?.toLowerCase() === 'manual'
      return [{ 
        description: null, 
        code: testCase, 
        filename: isManual ? 'manual_test_case.md' : 'test.py' 
      }]
    }
    
    return []
  }

  const downloadFile = (file: TestFile) => {
    const blob = new Blob([file.code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const downloadAllAsZip = async () => {
    const files = getTestFiles()
    if (files.length === 0) return

    try {
      // Динамический импорт JSZip
      const JSZip = (await import('jszip')).default
      const zip = new JSZip()
      
      files.forEach((file: TestFile) => {
        zip.file(file.filename, file.code)
      })
      
      // Добавляем README с описаниями
      const readmeParts: string[] = []
      readmeParts.push('# TestOps Copilot - Сгенерированные тесты\n')
      readmeParts.push(`Задача: ${taskId}\n`)
      readmeParts.push(`Тип: ${taskStatus?.result?.test_type || 'N/A'}\n`)
      readmeParts.push(`Приоритет: ${taskStatus?.result?.priority || 'N/A'}\n`)
      readmeParts.push('\n## Файлы:\n')
      
      files.forEach((file: TestFile) => {
        readmeParts.push(`\n### ${file.filename}\n`)
        if (file.description) {
          readmeParts.push(file.description)
          readmeParts.push('\n')
        }
      })
      
      zip.file('README.md', readmeParts.join('\n'))
      
      const content = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(content)
      const a = document.createElement('a')
      a.href = url
      a.download = `testops_tests_${taskId}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      // Если JSZip не доступен, скачиваем все файлы по отдельности
      console.error('Ошибка создания архива:', error)
      alert('Архивация недоступна. Скачиваю файлы по отдельности...')
      files.forEach((file: TestFile, index: number) => {
        setTimeout(() => downloadFile(file), index * 200)
      })
    }
  }

  const downloadArtifacts = () => {
    if (!taskStatus) return

    const metadata = {
      task_id: taskStatus.task_id,
      status: taskStatus.status,
      result: taskStatus.result,
      error: taskStatus.error,
    }

    const parts: string[] = []
    parts.push(`# TestOps Copilot артефакты для задачи ${taskStatus.task_id}`)
    parts.push(`Статус: ${taskStatus.status}`)
    if (taskStatus.result?.test_type) parts.push(`Тип: ${taskStatus.result.test_type}`)
    if (taskStatus.result?.feature) parts.push(`Фича: ${taskStatus.result.feature}`)
    if (taskStatus.result?.priority) parts.push(`Приоритет: ${taskStatus.result.priority}`)
    parts.push('')
    
    // Добавляем промпт, если он есть
    if (taskStatus.result?.prompt) {
      parts.push('--- промпт, отправленный в LLM ---')
      parts.push(taskStatus.result.prompt)
      parts.push('--- конец промпта ---')
      parts.push('')
    }
    
    // Обрабатываем новую структуру с файлами
    const files = getTestFiles()
    if (files.length > 0) {
      files.forEach((file: TestFile, index: number) => {
        parts.push(`--- файл ${index + 1}: ${file.filename} ---`)
        if (file.description) {
          parts.push(`Описание:\n${file.description}\n`)
        }
        parts.push('Код:')
        parts.push(file.code)
        parts.push(`--- конец файла ${index + 1} ---\n`)
      })
    } else if (taskStatus.result?.test_case) {
      // Fallback для старой структуры
      parts.push('--- начало кода ---')
      if (typeof taskStatus.result.test_case === 'string') {
        parts.push(taskStatus.result.test_case)
      } else {
        parts.push(JSON.stringify(taskStatus.result.test_case, null, 2))
      }
      parts.push('--- конец кода ---')
    } else {
      parts.push('Код ещё не готов.')
    }
    parts.push('')
    parts.push('--- сырые метаданные ---')
    parts.push(JSON.stringify(metadata, null, 2))

    const blob = new Blob([parts.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `artifacts_task_${taskStatus.task_id}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleRecreateTask = async () => {
    if (!taskStatus?.result) return

    setRecreating(true)
    setError(null)

    try {
      // Извлекаем описание из промпта, если оно есть, иначе используем общее описание
      let description = ''
      if (taskStatus.result.prompt) {
        // Пытаемся извлечь описание из промпта
        description = taskStatus.result.prompt
      } else {
        // Если промпта нет, создаем описание на основе доступных данных
        description = `Пересоздание задачи ${taskStatus.task_id}`
        if (taskStatus.result.feature) {
          description += `\nФича: ${taskStatus.result.feature}`
        }
      }

      const response = await generateTestCase({
        description,
        test_type: taskStatus.result.test_type || 'manual',
        feature: taskStatus.result.feature || undefined,
        story: taskStatus.result.story || undefined,
        priority: taskStatus.result.priority || 'NORMAL',
        owner: taskStatus.result.owner || undefined,
        jira_link: taskStatus.result.jira_link || undefined,
      })

      // Перенаправляем на новую задачу
      navigate(`/tasks/${response.task_id}`)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Не удалось пересоздать задачу'
      setError(errorMsg)
    } finally {
      setRecreating(false)
    }
  }

  const statusAppearance = taskStatus ? getStatusAppearance(taskStatus.status) : 'neutral'
  const statusLabel = taskStatus ? getStatusLabel(taskStatus.status) : 'Статус неизвестен'

  return (
    <div className="tasks-page">
      <div className="page-header">
        <h1>Задача {taskId}</h1>
        <p>Онлайн-статус генерации тест-кейса</p>
      </div>

      <div className="tasks-container">
        <Card>
          <div className="status-header">
            <div>
              <h3>Статус задачи</h3>
              <div className="detail-row">
                <strong>ID:</strong> <code>{taskId}</code>
              </div>
            </div>
            <Status label={statusLabel} appearance={statusAppearance} />
          </div>

          {error && <Alert appearance="error" title="Ошибка" description={error} />}

          {taskStatus?.progress && progressVisible && (
            <div className={`progress-section ${progressFading ? 'fade-out' : ''}`}>
              <p>
                Прогресс: {taskStatus.progress.current} / {taskStatus.progress.total} (
                {Math.round((taskStatus.progress.current / taskStatus.progress.total) * 100)}%)
              </p>
              <p className="progress-message">{taskStatus.progress.message}</p>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${(taskStatus.progress.current / taskStatus.progress.total) * 100}%` }}
                />
              </div>
            </div>
          )}

          {connecting && <p className="loading-inline">Подключаемся к WebSocket...</p>}

          {(taskStatus?.status === 'SUCCESS' || taskStatus?.status === 'completed') && taskStatus?.result && (
            <div className="result-section">
              <h4>Сгенерированный тест-кейс</h4>
              <div className="test-case-info">
                <div className="info-row">
                  <span>Тип:</span>
                  <span>{taskStatus.result.test_type || 'N/A'}</span>
                </div>
                {taskStatus.result.feature && (
                  <div className="info-row">
                    <span>Фича:</span>
                    <span>{taskStatus.result.feature}</span>
                  </div>
                )}
                <div className="info-row">
                  <span>Приоритет:</span>
                  <span>{taskStatus.result.priority || 'N/A'}</span>
                </div>
              </div>

              {(() => {
                const files = getTestFiles()
                if (files.length === 0) return null
                
                return (
                  <div className="test-files-section">
                    <div className="code-header" style={{ marginBottom: '1rem' }}>
                      <span>Сгенерированные файлы ({files.length})</span>
                      <div className="code-actions" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <ButtonFilled 
                          label="Скачать архив (ZIP)" 
                          onClick={downloadAllAsZip} 
                          size="s" 
                          appearance="primary" 
                        />
                        <ButtonFilled 
                          label="Скачать артефакты" 
                          onClick={downloadArtifacts} 
                          size="s" 
                          appearance="neutral" 
                        />
                      </div>
                    </div>
                    
                          {files.map((file: TestFile, index: number) => {
                      const isMarkdown = isMarkdownFile(file.filename)
                      return (
                        <div key={index} className={isMarkdown ? "markdown-preview" : "code-preview"} style={{ marginBottom: '1.5rem' }}>
                          <div className="code-header">
                            <span>
                              <strong>{file.filename}</strong>
                              {isMarkdown && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: '#667eea', background: '#f0f0ff', padding: '0.125rem 0.5rem', borderRadius: '4px' }}>Markdown</span>}
                            </span>
                            <div className="code-actions">
                              <ButtonFilled 
                                label="Скачать файл" 
                                onClick={() => downloadFile(file)} 
                                size="s" 
                                appearance="neutral" 
                              />
                            </div>
                          </div>
                          {isMarkdown ? (
                            <div className="markdown-content">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {file.code}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <pre className="code-content">{file.code}</pre>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )
              })()}
            </div>
          )}

          {(taskStatus?.status === 'FAILURE' || taskStatus?.status === 'failed') && taskStatus?.error && (
            <Alert appearance="error" title="Ошибка" description={taskStatus.error} />
          )}

          {(taskStatus?.status === 'PENDING' ||
            taskStatus?.status === 'PROGRESS' ||
            taskStatus?.status === 'pending' ||
            taskStatus?.status === 'in_progress') && (
            <div className="pending-section">
              <p>Задача обрабатывается...</p>
              <div className="loader">Загрузка...</div>
            </div>
          )}

          <div className="history-actions" style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <ButtonFilled label="К списку задач" appearance="neutral" onClick={() => navigate('/tasks')} />
            {isTerminal(taskStatus?.status) && taskStatus?.result && (
              <ButtonFilled 
                label={recreating ? 'Пересоздание...' : 'Пересоздать задачу'} 
                appearance="primary" 
                onClick={handleRecreateTask}
                disabled={recreating}
                loading={recreating}
              />
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}


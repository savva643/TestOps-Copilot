import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert } from '@snack-uikit/alert'
import { ButtonFilled } from '@snack-uikit/button'
import { Card } from '@snack-uikit/card'
import { Status } from '@snack-uikit/status'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getTaskStatus, getTasksWebSocketUrl } from '../api/tasks'
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
  const [error, setError] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [progressVisible, setProgressVisible] = useState(true)
  const [progressFading, setProgressFading] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const isTerminal = (status?: string) => {
    if (!status) return false
    const s = status.toUpperCase()
    return s !== 'PENDING' && s !== 'PROGRESS' && s !== 'IN_PROGRESS' && s !== 'PENDING'
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

  const connectWebSocket = () => {
    if (!taskId) return
    setConnecting(true)
    const url = getTasksWebSocketUrl(taskId)
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnecting(false)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setTaskStatus(data)
          setError(null)
          if (isTerminal(data.status)) {
            ws.close()
          }
        } catch (err) {
          console.error('WS parse error', err)
        }
      }

      ws.onerror = () => {
        setConnecting(false)
        setError('Ошибка WebSocket, переключаемся на опрос.')
        ws.close()
      }

      ws.onclose = () => {
        wsRef.current = null
      }
    } catch (err: any) {
      setConnecting(false)
      setError(err.message || 'Не удалось подключиться к WebSocket')
    }
  }

  const fetchOnce = async () => {
    if (!taskId) return
    try {
      const status = await getTaskStatus(taskId)
      setTaskStatus(status)
      setError(null)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Не удалось получить статус задачи'
      setError(errorMsg)
    }
  }

  useEffect(() => {
    fetchOnce()
    connectWebSocket()
    return () => {
      wsRef.current?.close()
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
                      <div className="code-actions">
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
                              {file.description && <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: '#666' }}>с описанием</span>}
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
                          {file.description && (
                            <div style={{ padding: '0.75rem', background: '#f5f5f5', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
                              {file.description}
                            </div>
                          )}
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

          <div className="history-actions" style={{ marginTop: '1rem' }}>
            <ButtonFilled label="К списку задач" appearance="neutral" onClick={() => navigate('/tasks')} />
          </div>
        </Card>
      </div>
    </div>
  )
}


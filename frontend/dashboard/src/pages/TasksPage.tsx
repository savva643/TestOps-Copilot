import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getTaskStatus, getTasks, TaskListItem } from '../api/tasks'
import { Card } from '@snack-uikit/card'
import { ButtonFilled } from '@snack-uikit/button'
import { Status } from '@snack-uikit/status'
import { Alert } from '@snack-uikit/alert'
import { getStoredCredentials } from '../api/auth'
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

export function TasksPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [taskId, setTaskId] = useState('')
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)
  const [tasks, setTasks] = useState<TaskListItem[]>([])
  const [tasksPage, setTasksPage] = useState(1)
  const [totalTasks, setTotalTasks] = useState(0)
  const [listLoading, setListLoading] = useState(false)
  const credentials = useMemo(() => getStoredCredentials(), [])
  const ownerId = credentials?.keyId
  const pageSize = 10

  useEffect(() => {
    const paramTaskId = searchParams.get('taskId')
    if (paramTaskId) {
      setTaskId(paramTaskId)
      handleCheck(paramTaskId)
    }
  }, [])

  useEffect(() => {
    fetchTasks()
  }, [tasksPage, ownerId])

  const handleCheck = async (idToCheck?: string) => {
    const id = idToCheck ?? taskId
    if (!id.trim()) {
      setError('Пожалуйста, введите ID задачи')
      return
    }

    setLoading(true)
    setError(null)

    try {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('taskId', id)
        return next
      })
      // Проверяем, что задача существует (если не существует, будет выброшена ошибка)
      await getTaskStatus(id)
      
      // Если задача существует, перенаправляем на страницу деталей задачи
      navigate(`/tasks/${id}`)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Не удалось получить статус задачи'
      // Если 404 или похожая ошибка, показываем сообщение о несуществующей задаче
      if (err.response?.status === 404 || errorMsg.toLowerCase().includes('not found') || errorMsg.toLowerCase().includes('не найдена')) {
        setError('Задача с таким ID не найдена в базе данных')
      } else {
        setError(errorMsg)
      }
      setTaskStatus(null)
      setPolling(false)
    } finally {
      setLoading(false)
    }
  }

  const fetchTasks = async () => {
    try {
      setListLoading(true)
      const params: { page: number; page_size: number; owner_id?: string } = {
        page: tasksPage,
        page_size: pageSize,
      }
      // Всегда фильтруем по owner_id текущего пользователя
      if (ownerId) {
        params.owner_id = ownerId
      }
      const response = await getTasks(params)
      setTasks(response.items)
      setTotalTasks(response.total)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Не удалось загрузить список задач'
      setError(errorMsg)
    } finally {
      setListLoading(false)
    }
  }

  useEffect(() => {
    if (!polling || !taskId) return

    const interval = setInterval(async () => {
      try {
        const status = await getTaskStatus(taskId)
        setTaskStatus(status)

        if (status.status !== 'pending' && status.status !== 'in_progress' && status.status !== 'PENDING' && status.status !== 'PROGRESS') {
          setPolling(false)
          fetchTasks()
        }
      } catch (err) {
        console.error('Ошибка опроса:', err)
        setPolling(false)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [polling, taskId])

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
      return [{ description: null, code: testCase, filename: 'test.py' }]
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
      const JSZip = (await import('jszip')).default
      const zip = new JSZip()
      
      files.forEach((file: TestFile) => {
        zip.file(file.filename, file.code)
      })
      
      const readmeParts: string[] = []
      readmeParts.push('# TestOps Copilot - Сгенерированные тесты\n')
      readmeParts.push(`Задача: ${taskStatus?.task_id}\n`)
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
      a.download = `testops_tests_${taskStatus?.task_id}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
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

  const handleHistoryClick = (historyTaskId: string) => {
    setTaskId(historyTaskId)
    handleCheck(historyTaskId)
    navigate(`/tasks/${historyTaskId}`)
  }

  const totalPages = Math.max(1, Math.ceil(totalTasks / pageSize))

  return (
    <div className="tasks-page">
      <div className="page-header">
        <h1>Задачи</h1>
        <p>Проверьте статус генерации тест-кейсов и скачайте результаты</p>
      </div>

      <div className="tasks-container">
        <Card>
          <div className="search-form">
            <div className="form-group">
              <label htmlFor="taskId">ID задачи</label>
              <input
                id="taskId"
                type="text"
                className="task-input"
                value={taskId}
                onChange={(e) => setTaskId(e.target.value)}
                placeholder="Введите ID задачи"
                onKeyPress={(e: React.KeyboardEvent) => {
                  if (e.key === 'Enter') {
                    handleCheck()
                  }
                }}
              />
            </div>
            <div className="button-wrapper">
              <ButtonFilled
                label={loading ? 'Проверка...' : 'Проверить статус'}
                onClick={() => handleCheck()}
                disabled={loading || !taskId.trim()}
                loading={loading}
                size="l"
                className="check-status-button"
              />
            </div>
          </div>

          {error && (
            <Alert appearance="error" title="Ошибка" description={error} />
          )}
        </Card>

        {tasks.length > 0 && (
          <Card className="history-card">
            <div className="history-header">
              <h3>Мои задачи</h3>
              <div className="history-actions">
                <div className="pagination">
                  <ButtonFilled
                    label="Назад"
                    size="s"
                    disabled={tasksPage === 1 || listLoading}
                    onClick={() => setTasksPage((p) => Math.max(1, p - 1))}
                  />
                  <span className="pagination-info">
                    Страница {tasksPage} из {totalPages}
                  </span>
                  <ButtonFilled
                    label="Вперёд"
                    size="s"
                    disabled={tasksPage >= totalPages || listLoading}
                    onClick={() => setTasksPage((p) => p + 1)}
                  />
                </div>
              </div>
            </div>
            <div className="history-list">
              {tasks.map((item) => (
                <div
                  key={item.task_id}
                  className="history-item"
                  onClick={() => handleHistoryClick(item.task_id)}
                >
                  <div className="history-item-main">
                    <code className="history-task-id">{item.task_id}</code>
                    <Status
                      label={getStatusLabel(item.status)}
                      appearance={getStatusAppearance(item.status)}
                      size="s"
                    />
                  </div>
                  <div className="history-item-meta">
                    <span>{item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : '—'}</span>
                    {item.test_type && <span className="test-type-badge">{item.test_type}</span>}
                    {item.is_gitlab_task === 'true' && (
                      <span className="gitlab-badge" style={{ background: '#fc6d26', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem' }}>
                        GitLab
                      </span>
                    )}
                  </div>
                  {item.gitlab_merge_request_url && (
                    <div style={{ marginTop: '0.5rem' }}>
                      <a
                        href={item.gitlab_merge_request_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        style={{ color: '#fc6d26', fontSize: '0.875rem', textDecoration: 'none' }}
                      >
                        → Merge Request
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
            {listLoading && <p className="loading-inline">Загрузка списка задач...</p>}
            {!listLoading && tasks.length === 0 && <p>Задач пока нет.</p>}
          </Card>
        )}

        {taskStatus && (
          <Card>
            <div className="status-header">
              <h3>Статус задачи</h3>
              <Status
                label={getStatusLabel(taskStatus.status)}
                appearance={getStatusAppearance(taskStatus.status)}
              />
            </div>

            <div className="task-details">
              <div className="detail-row">
                <strong>ID задачи:</strong>
                <code>{taskStatus.task_id}</code>
              </div>

              {taskStatus.progress && (
                <div className="progress-section">
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

              {(taskStatus.status === 'SUCCESS' || taskStatus.status === 'completed') && taskStatus.result && (
                <>
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
                          
                          {files.map((file: TestFile, index: number) => (
                            <div key={index} className="code-preview" style={{ marginBottom: '1.5rem' }}>
                              <div className="code-header">
                                <span>
                                  <strong>{file.filename}</strong>
                                  {file.description && <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: '#666' }}>с описанием</span>}
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
                              <pre className="code-content">{file.code}</pre>
                            </div>
                          ))}
                        </div>
                      )
                    })()}
                  </div>
                </>
              )}

              {(taskStatus.status === 'FAILURE' || taskStatus.status === 'failed') && taskStatus.error && (
                <Alert appearance="error" title="Ошибка" description={taskStatus.error} />
              )}

              {(taskStatus.status === 'PENDING' || taskStatus.status === 'PROGRESS' || taskStatus.status === 'pending' || taskStatus.status === 'in_progress') && (
                <div className="pending-section">
                  <p>Задача обрабатывается...</p>
                  <div className="loader">Загрузка...</div>
                </div>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

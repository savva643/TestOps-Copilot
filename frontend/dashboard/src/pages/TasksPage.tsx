import { useState, useEffect } from 'react'
import { getTaskStatus } from '../api/tasks'
import { Card } from '@snack-uikit/card'
import { ButtonFilled } from '@snack-uikit/button'
import { Status } from '@snack-uikit/status'
import { Alert } from '@snack-uikit/alert'
import { getStoredCredentials } from '../api/auth'
import './TasksPage.css'

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

interface TaskHistoryItem {
  task_id: string
  status: string
  created_at: string
  test_type?: string
}

export function TasksPage() {
  const [taskId, setTaskId] = useState('')
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([])

  useEffect(() => {
    // Загружаем историю задач из localStorage
    const history = JSON.parse(localStorage.getItem('task_history') || '[]')
    setTaskHistory(history)
  }, [])

  const handleCheck = async () => {
    if (!taskId.trim()) {
      setError('Пожалуйста, введите ID задачи')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const status = await getTaskStatus(taskId)
      setTaskStatus(status)
      
      if (status.status === 'pending' || status.status === 'in_progress' || status.status === 'PENDING' || status.status === 'PROGRESS') {
        setPolling(true)
      } else {
        setPolling(false)
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Не удалось получить статус задачи'
      setError(errorMsg)
      setTaskStatus(null)
      setPolling(false)
    } finally {
      setLoading(false)
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
          // Обновляем историю
          const history = JSON.parse(localStorage.getItem('task_history') || '[]')
          const updatedHistory = history.map((item: TaskHistoryItem) =>
            item.task_id === taskId ? { ...item, status: status.status } : item
          )
          localStorage.setItem('task_history', JSON.stringify(updatedHistory))
          setTaskHistory(updatedHistory)
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

  const downloadCode = () => {
    if (!taskStatus?.result?.test_case) return

    const blob = new Blob([taskStatus.result.test_case], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `test_case_${taskId}.py`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
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
    parts.push('--- начало кода ---')
    if (taskStatus.result?.test_case) {
      parts.push(taskStatus.result.test_case)
    } else {
      parts.push('Код ещё не готов.')
    }
    parts.push('--- конец кода ---')
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
    handleCheck()
  }

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
                onClick={handleCheck}
                disabled={loading || !taskId.trim()}
                loading={loading}
              />
            </div>
          </div>

          {error && (
            <Alert appearance="error" title="Ошибка" description={error} />
          )}
        </Card>

        {taskHistory.length > 0 && (
          <Card className="history-card">
            <h3>История задач</h3>
            <div className="history-list">
              {taskHistory.map((item) => (
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
                    <span>{new Date(item.created_at).toLocaleString('ru-RU')}</span>
                    {item.test_type && <span className="test-type-badge">{item.test_type}</span>}
                  </div>
                </div>
              ))}
            </div>
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
                      <div className="info-row">
                        <span>Фича:</span>
                        <span>{taskStatus.result.feature || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span>Приоритет:</span>
                        <span>{taskStatus.result.priority || 'N/A'}</span>
                      </div>
                    </div>

                    {taskStatus.result.test_case && (
                      <div className="code-preview">
                        <div className="code-header">
                          <span>Сгенерированный код</span>
                          <div className="code-actions">
                            <ButtonFilled label="Скачать код" onClick={downloadCode} size="s" appearance="primary" />
                            <ButtonFilled label="Скачать артефакты" onClick={downloadArtifacts} size="s" appearance="neutral" />
                          </div>
                        </div>
                        <pre className="code-content">
                          {taskStatus.result.test_case}
                        </pre>
                      </div>
                    )}
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

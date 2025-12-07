import { useState, useEffect } from 'react'
import { getTaskStatus } from '../api/tasks'
import './TasksPage.css'

interface TaskStatus {
  task_id: string
  status: string
  result?: any
  error?: string
}

export function TasksPage() {
  const [taskId, setTaskId] = useState('')
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)

  const handleCheck = async () => {
    if (!taskId.trim()) {
      setError('Please enter a task ID')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const status = await getTaskStatus(taskId)
      setTaskStatus(status)
      
      // Auto-poll if task is pending
      if (status.status === 'pending') {
        setPolling(true)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to get task status')
      setTaskStatus(null)
    } finally {
      setLoading(false)
    }
  }

  // Auto-poll for pending tasks
  useEffect(() => {
    if (!polling || !taskId) return

    const interval = setInterval(async () => {
      try {
        const status = await getTaskStatus(taskId)
        setTaskStatus(status)

        if (status.status !== 'pending') {
          setPolling(false)
        }
      } catch (err) {
        console.error('Polling error:', err)
        setPolling(false)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [polling, taskId])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'error'
      case 'pending':
        return 'warning'
      default:
        return 'info'
    }
  }

  const downloadCode = () => {
    if (!taskStatus?.result?.code) return

    const blob = new Blob([taskStatus.result.code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `test_case_${taskId}.py`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="tasks-page">
      <div className="page-header">
        <h1>Task Status</h1>
        <p>Check the status of test generation tasks</p>
      </div>

      <div className="tasks-container">
        <div className="task-search-card">
          <div className="search-form">
            <input
              type="text"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="Enter task ID"
              className="task-input"
              onKeyPress={(e) => e.key === 'Enter' && handleCheck()}
            />
            <button
              onClick={handleCheck}
              disabled={loading || !taskId.trim()}
              className="check-button"
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Checking...
                </>
              ) : (
                'Check Status'
              )}
            </button>
          </div>

          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {taskStatus && (
          <div className="task-status-card">
            <div className="status-header">
              <h3>Task Status</h3>
              <span className={`status-badge ${getStatusColor(taskStatus.status)}`}>
                {taskStatus.status.toUpperCase()}
              </span>
            </div>

            <div className="task-details">
              <div className="detail-row">
                <strong>Task ID:</strong>
                <code>{taskStatus.task_id}</code>
              </div>

              {taskStatus.status === 'completed' && taskStatus.result && (
                <>
                  <div className="result-section">
                    <h4>Generated Test Case</h4>
                    <div className="test-case-info">
                      <div className="info-row">
                        <span>Type:</span>
                        <span>{taskStatus.result.test_type || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span>Feature:</span>
                        <span>{taskStatus.result.feature || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span>Priority:</span>
                        <span>{taskStatus.result.priority || 'N/A'}</span>
                      </div>
                    </div>

                    {taskStatus.result.test_case && (
                      <div className="code-preview">
                        <div className="code-header">
                          <span>Generated Code</span>
                          <button onClick={downloadCode} className="download-button">
                            Download
                          </button>
                        </div>
                        <pre className="code-content">
                          {taskStatus.result.test_case}
                        </pre>
                      </div>
                    )}
                  </div>
                </>
              )}

              {taskStatus.status === 'failed' && taskStatus.error && (
                <div className="error-section">
                  <strong>Error:</strong>
                  <pre>{taskStatus.error}</pre>
                </div>
              )}

              {taskStatus.status === 'pending' && (
                <div className="pending-section">
                  <p>Task is being processed...</p>
                  <div className="progress-bar">
                    <div className="progress-fill"></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

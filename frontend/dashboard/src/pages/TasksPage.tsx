import { useState, useEffect } from 'react'
import { getTaskStatus } from '../api/tasks'
import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { ButtonFilled } from '@snack-uikit/button'
import { TextField } from '@snack-uikit/fields'
import { Status } from '@snack-uikit/status'
import { Alert } from '@snack-uikit/alert'
import { Divider } from '@snack-uikit/divider'
import { Loader } from '@snack-uikit/loaders'
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
    }, 2000)

    return () => clearInterval(interval)
  }, [polling, taskId])

  const getStatusAppearance = (status: string): 'positive' | 'negative' | 'warning' | 'neutral' => {
    switch (status) {
      case 'completed':
        return 'positive'
      case 'failed':
        return 'negative'
      case 'pending':
        return 'warning'
      default:
        return 'neutral'
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
        <Typography variant="h1" size="xl">Task Status</Typography>
        <Typography variant="body" size="m">Check the status of test generation tasks</Typography>
      </div>

      <Divider />

      <div className="tasks-container">
        <Card>
          <div className="search-form">
            <TextField
              label="Task ID"
              value={taskId}
              onChange={(value) => setTaskId(value)}
              placeholder="Enter task ID"
              onKeyPress={(e) => e.key === 'Enter' && handleCheck()}
            />
            <ButtonFilled
              label={loading ? 'Checking...' : 'Check Status'}
              onClick={handleCheck}
              disabled={loading || !taskId.trim()}
              loading={loading}
            />
          </div>

          {error && (
            <Alert appearance="negative" title="Error" description={error} />
          )}
        </Card>

        {taskStatus && (
          <Card>
            <div className="status-header">
              <Typography variant="h3" size="m">Task Status</Typography>
              <Status label={taskStatus.status.toUpperCase()} appearance={getStatusAppearance(taskStatus.status)} />
            </div>

            <Divider />

            <div className="task-details">
              <div className="detail-row">
                <Typography variant="body" size="m"><strong>Task ID:</strong></Typography>
                <code>{taskStatus.task_id}</code>
              </div>

              {taskStatus.status === 'completed' && taskStatus.result && (
                <>
                  <Divider />
                  <div className="result-section">
                    <Typography variant="h4" size="m">Generated Test Case</Typography>
                    <div className="test-case-info">
                      <div className="info-row">
                        <Typography variant="body" size="m">Type:</Typography>
                        <Typography variant="body" size="m">{taskStatus.result.test_type || 'N/A'}</Typography>
                      </div>
                      <div className="info-row">
                        <Typography variant="body" size="m">Feature:</Typography>
                        <Typography variant="body" size="m">{taskStatus.result.feature || 'N/A'}</Typography>
                      </div>
                      <div className="info-row">
                        <Typography variant="body" size="m">Priority:</Typography>
                        <Typography variant="body" size="m">{taskStatus.result.priority || 'N/A'}</Typography>
                      </div>
                    </div>

                    {taskStatus.result.test_case && (
                      <div className="code-preview">
                        <div className="code-header">
                          <Typography variant="body" size="m">Generated Code</Typography>
                          <ButtonFilled label="Download" onClick={downloadCode} size="s" />
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
                <Alert appearance="negative" title="Error" description={taskStatus.error} />
              )}

              {taskStatus.status === 'pending' && (
                <div className="pending-section">
                  <Typography variant="body" size="m">Task is being processed...</Typography>
                  <Loader size="m" />
                </div>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

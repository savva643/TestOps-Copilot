import { useEffect, useState, useMemo } from 'react'
import { Card } from '@snack-uikit/card'
import { ButtonFilled } from '@snack-uikit/button'
import { Status } from '@snack-uikit/status'
import { Link } from 'react-router-dom'
import { getTasks, TaskListItem } from '../api/tasks'
import { getStoredCredentials } from '../api/auth'
import './DashboardPage.css'

const statusAppearanceMap: Record<string, 'green' | 'yellow' | 'red' | 'neutral'> = {
  completed: 'green',
  success: 'green',
  pending: 'yellow',
  in_progress: 'yellow',
  progress: 'yellow',
  failed: 'red',
  failure: 'red',
}

function getStatusAppearance(status: string): 'green' | 'yellow' | 'red' | 'neutral' {
  const statusUpper = status.toUpperCase()
  if (statusUpper === 'SUCCESS' || statusUpper === 'COMPLETED') return 'green'
  if (statusUpper === 'FAILURE' || statusUpper === 'FAILED') return 'red'
  if (statusUpper === 'PENDING' || statusUpper === 'PROGRESS' || statusUpper === 'IN_PROGRESS') return 'yellow'
  return statusAppearanceMap[status.toLowerCase()] || 'neutral'
}

function getStatusLabel(status: string): string {
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

export function DashboardPage() {
  const credentials = useMemo(() => getStoredCredentials(), [])
  const ownerId = credentials?.keyId
  const [tasks, setTasks] = useState<TaskListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTasks()
  }, [ownerId])

  const fetchTasks = async () => {
    try {
      setLoading(true)
      setError(null)
      const params: { page: number; page_size: number; owner_id?: string } = {
        page: 1,
        page_size: 10,
      }
      if (ownerId) {
        params.owner_id = ownerId
      }
      const response = await getTasks(params)
      setTasks(response.items)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Не удалось загрузить задачи'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  // Вычисляем статистику из реальных данных
  const stats = useMemo(() => {
    const total = tasks.length
    const completed = tasks.filter((t) => t.status.toUpperCase() === 'SUCCESS' || t.status.toUpperCase() === 'COMPLETED').length
    const pending = tasks.filter((t) => {
      const s = t.status.toUpperCase()
      return s === 'PENDING' || s === 'PROGRESS' || s === 'IN_PROGRESS'
    }).length
    const failed = tasks.filter((t) => t.status.toUpperCase() === 'FAILURE' || t.status.toUpperCase() === 'FAILED').length

    return [
      { title: 'Всего задач', value: total.toString(), hint: 'созданных вами' },
      { title: 'Завершено', value: completed.toString(), hint: 'успешно выполнено' },
      { title: 'В процессе', value: pending.toString(), hint: 'ожидают выполнения' },
      { title: 'Ошибки', value: failed.toString(), hint: 'требуют внимания' },
    ]
  }, [tasks])

  // Последние задачи (первые 5)
  const recentTasks = useMemo(() => {
    return tasks.slice(0, 5).map((task) => ({
      id: task.task_id,
      type: (task.test_type || 'manual').toUpperCase(),
      status: task.status,
      createdAt: task.created_at ? new Date(task.created_at).toLocaleString('ru-RU') : '—',
    }))
  }, [tasks])

  // Завершенные задачи с результатами
  const completedTasks = useMemo(() => {
    return tasks
      .filter((t) => {
        const s = t.status.toUpperCase()
        return s === 'SUCCESS' || s === 'COMPLETED'
      })
      .slice(0, 5)
      .map((task) => ({
        id: task.task_id,
        type: (task.test_type || 'manual').toUpperCase(),
        title: task.test_type ? `Тест ${task.test_type}` : 'Тест',
        updated: task.updated_at ? new Date(task.updated_at).toLocaleDateString('ru-RU') : '—',
      }))
  }, [tasks])

  // Лёгкий мониторинг: успех, средняя длительность, GitLab-задачи, очередь
  const monitoringCards = useMemo(() => {
    const completed = tasks.filter((t) => {
      const s = t.status.toUpperCase()
      return s === 'SUCCESS' || s === 'COMPLETED'
    })
    const failed = tasks.filter((t) => {
      const s = t.status.toUpperCase()
      return s === 'FAILURE' || s === 'FAILED'
    })
    const pending = tasks.filter((t) => {
      const s = t.status.toUpperCase()
      return s === 'PENDING' || s === 'PROGRESS' || s === 'IN_PROGRESS'
    })

    const successBase = completed.length + failed.length
    const successRate = successBase > 0 ? `${Math.round((completed.length / successBase) * 100)}%` : '—'

    const durationsSeconds = completed
      .map((t) => {
        if (!t.created_at || !t.updated_at) return null
        const start = new Date(t.created_at).getTime()
        const end = new Date(t.updated_at).getTime()
        if (Number.isNaN(start) || Number.isNaN(end) || end <= start) return null
        return Math.round((end - start) / 1000)
      })
      .filter((v): v is number => v !== null)

    const avgDuration =
      durationsSeconds.length > 0
        ? (() => {
            const avg = durationsSeconds.reduce((a, b) => a + b, 0) / durationsSeconds.length
            if (avg >= 90) return `${Math.round(avg / 60)} мин`
            return `${Math.round(avg)} сек`
          })()
        : '—'

    const gitlabTasks = tasks.filter((t) => t.is_gitlab_task === 'true' || t.gitlab_url).length

    return [
      { title: 'Успех задач', value: successRate, hint: 'SUCCESS / (SUCCESS + FAILED)' },
      { title: 'Средняя длительность', value: avgDuration, hint: 'для завершённых задач' },
      { title: 'GitLab задачи', value: gitlabTasks.toString(), hint: 'c GitLab URL/MR' },
      { title: 'В очереди', value: pending.length.toString(), hint: 'PENDING / IN_PROGRESS' },
    ]
  }, [tasks])

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">TestOps Copilot — Дашборд</h1>
          <p className="page-subtitle">Быстрый обзор состояния генерации и оптимизации тестов</p>
        </div>
        <div className="header-actions">
          <Link to="/generate">
            <ButtonFilled label="Сгенерировать тесты" size="m" className="btn-primary" />
          </Link>
          <Link to="/tasks">
            <ButtonFilled label="Все задачи" size="m" className="btn-secondary" />
          </Link>
        </div>
      </div>

      <div className="stats-grid">
        {stats.map((item) => (
          <Card key={item.title} className="stat-card">
            <h3>{item.title}</h3>
            <div className="stat-value">{item.value}</div>
            <p className="stat-hint">{item.hint}</p>
          </Card>
        ))}
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Мониторинг</h3>
            <p className="panel-hint">Качество выполнения задач и очередь (live из API)</p>
          </div>
          <div className="panel-actions">
            <ButtonFilled label="Обновить" size="s" appearance="primary" onClick={fetchTasks} />
          </div>
        </div>
        <div className="monitoring-grid">
          {monitoringCards.map((item) => (
            <Card key={item.title} className="stat-card">
              <h3>{item.title}</h3>
              <div className="stat-value">{item.value}</div>
              <p className="stat-hint">{item.hint}</p>
            </Card>
          ))}
        </div>
      </div>

      <div className="cta-grid">
        <Card className="cta-card">
          <h3>Создать новую задачу</h3>
          <p className="cta-hint">
            Загрузите OpenAPI/YAML/JSON или текстовое описание — мы разберём и подготовим тесты
          </p>
          <Link to="/generate">
            <ButtonFilled label="Сгенерировать тесты" size="m" className="btn-primary" />
          </Link>
        </Card>
        <Card className="cta-card">
          <h3>Мои задачи</h3>
          <p className="cta-hint">
            Следите за прогрессом генерации, смотрите статусы и забирайте готовые артефакты
          </p>
          <Link to="/tasks">
            <ButtonFilled label="Открыть задачи" size="m" className="btn-secondary" />
          </Link>
        </Card>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Последние задачи</h3>
            <p className="panel-hint">Мониторьте статус генерации и скачивайте результаты</p>
          </div>
          <div className="panel-actions">
            <ButtonFilled label="Обновить" size="s" appearance="primary" onClick={fetchTasks} />
          </div>
        </div>

        <div className="table-wrapper">
          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center' }}>Загрузка...</div>
          ) : error ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>{error}</div>
          ) : recentTasks.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              Задач пока нет. Создайте первую задачу!
            </div>
          ) : (
            <>
              <div className="table-head">
                <span>ID</span>
                <span>Тип</span>
                <span>Статус</span>
                <span>Создано</span>
              </div>
              {recentTasks.map((row) => (
                <Link key={row.id} to={`/tasks/${row.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className="table-row" style={{ cursor: 'pointer' }}>
                    <span>{row.id}</span>
                    <span>{row.type}</span>
                    <span>
                      <Status label={getStatusLabel(row.status)} appearance={getStatusAppearance(row.status)} size="s" />
                    </span>
                    <span>{row.createdAt}</span>
                  </div>
                </Link>
              ))}
            </>
          )}
        </div>
      </div>

      {completedTasks.length > 0 && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Завершенные задачи</h3>
              <p className="panel-hint">Готовые тест-кейсы, которые можно скачать</p>
            </div>
            <div className="panel-actions">
              <Link to="/tasks">
                <ButtonFilled label="Все задачи" size="s" />
              </Link>
            </div>
          </div>

          <div className="table-wrapper">
            <div className="table-head cases-head">
              <span>ID</span>
              <span>Тип</span>
              <span>Название</span>
              <span>Обновлено</span>
              <span />
            </div>
            {completedTasks.map((row) => (
              <Link key={row.id} to={`/tasks/${row.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="table-row cases-row" style={{ cursor: 'pointer' }}>
                  <span>{row.id}</span>
                  <span>{row.type}</span>
                  <span className="ellipsis">{row.title}</span>
                  <span>{row.updated}</span>
                  <span className="download-cell">
                    <ButtonFilled label="Открыть" size="s" appearance="neutral" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

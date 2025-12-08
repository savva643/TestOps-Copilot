import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { ButtonFilled } from '@snack-uikit/button'
import { Divider } from '@snack-uikit/divider'
import { Status } from '@snack-uikit/status'
import './DashboardPage.css'

type TaskRow = {
  id: string
  type: 'manual' | 'api' | 'ui'
  status: 'completed' | 'pending' | 'failed'
  createdAt: string
}

const statusAppearanceMap: Record<TaskRow['status'], 'green' | 'yellow' | 'red'> = {
  completed: 'green',
  pending: 'yellow',
  failed: 'red',
}

const recentTasks: TaskRow[] = [
  { id: 'T-10023', type: 'api', status: 'completed', createdAt: '2025-02-12 14:20' },
  { id: 'T-10022', type: 'ui', status: 'pending', createdAt: '2025-02-12 14:10' },
  { id: 'T-10021', type: 'manual', status: 'failed', createdAt: '2025-02-12 13:55' },
  { id: 'T-10020', type: 'api', status: 'completed', createdAt: '2025-02-12 13:30' },
]

const stats = [
  { title: 'Всего тестов', value: '1 248', hint: 'за последние 30 дней' },
  { title: 'Активные задачи', value: '37', hint: 'в очереди генерации' },
  { title: 'Покрытие', value: '82%', hint: 'по ключевым сервисам' },
  { title: 'Ошибки', value: '5', hint: 'требуют внимания' },
]

export function DashboardPage() {
  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div>
          <Typography family="sans" purpose="title" size="l">
            TestOps Copilot — Дашборд
          </Typography>
          <Typography family="sans" purpose="body" size="m" className="page-subtitle">
            Быстрый обзор состояния генерации и оптимизации тестов
          </Typography>
        </div>
        <div className="header-actions">
          <ButtonFilled label="Создать задачу" size="m" />
        </div>
      </div>

      <div className="stats-grid">
        {stats.map((item) => (
          <Card key={item.title} className="stat-card">
            <Typography family="sans" purpose="title" size="s">
              {item.title}
            </Typography>
            <Typography family="sans" purpose="display" size="l" className="stat-value">
              {item.value}
            </Typography>
            <Typography family="sans" purpose="body" size="s" className="stat-hint">
              {item.hint}
            </Typography>
          </Card>
        ))}
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <Typography family="sans" purpose="title" size="m">
              Последние задачи
            </Typography>
            <Typography family="sans" purpose="body" size="s" className="panel-hint">
              Мониторьте статус генерации и скачивайте результаты
            </Typography>
          </div>
          <div className="panel-actions">
            <ButtonFilled label="Обновить" size="s" appearance="primary" />
          </div>
        </div>

        <div className="table-wrapper">
          <div className="table-head">
            <span>ID</span>
            <span>Тип</span>
            <span>Статус</span>
            <span>Создано</span>
          </div>
          {recentTasks.map((row) => (
            <div key={row.id} className="table-row">
              <span>{row.id}</span>
              <span>{row.type}</span>
              <span>
                <Status
                  label={row.status.toUpperCase()}
                  appearance={statusAppearanceMap[row.status]}
                  size="s"
                />
              </span>
              <span>{row.createdAt}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}


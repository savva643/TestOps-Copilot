import { Card } from '@snack-uikit/card'
import { ButtonFilled } from '@snack-uikit/button'
import { ButtonOutline } from '@snack-uikit/button'
import { Status } from '@snack-uikit/status'
import { Link } from 'react-router-dom'
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

const myTestCases = [
  { id: 'UI-CALC-001', type: 'UI', title: 'Калькулятор цен — базовый сценарий', updated: '2025-02-12' },
  { id: 'API-VM-015', type: 'API', title: 'Создание VM — позитивный путь', updated: '2025-02-11' },
]

const demoCases = [
  { id: 'DEMO-UI-001', title: 'UI калькулятор — 25 ручных кейсов + e2e Playwright', updated: 'готово' },
  { id: 'DEMO-API-001', title: 'API Compute — 25 ручных кейсов + pytest', updated: 'готово' },
]

export function DashboardPage() {
  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">TestOps Copilot — Дашборд</h1>
          <p className="page-subtitle">Быстрый обзор состояния генерации и оптимизации тестов</p>
        </div>
        <div className="header-actions">
          <Link to="/generate">
            <ButtonFilled label="Загрузить спецификацию" size="m" className="btn-primary" />
          </Link>
          <Link to="/generate">
            <ButtonFilled label="Сгенерировать тесты" size="m" className="btn-secondary" />
          </Link>
          <Link to="/tasks">
            <ButtonOutline label="Перейти к задачам" size="m" appearance="neutral" />
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

      <div className="cta-grid">
        <Card className="cta-card">
          <h3>Начните с загрузки</h3>
          <p className="cta-hint">
            Загрузите OpenAPI/YAML/JSON или текстовое описание — мы разберём и подготовим тесты
          </p>
          <Link to="/generate">
            <ButtonFilled label="Загрузить спецификацию" size="m" className="btn-primary" />
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

      <div className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Мои тест-кейсы</h3>
            <p className="panel-hint">Скачайте готовые артефакты или перейдите к задачам за свежими результатами</p>
          </div>
          <div className="panel-actions">
            <Link to="/tasks">
              <ButtonFilled label="Перейти к задачам" size="s" />
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
          {myTestCases.map((row) => (
            <div key={row.id} className="table-row cases-row">
              <span>{row.id}</span>
              <span>{row.type}</span>
              <span className="ellipsis">{row.title}</span>
              <span>{row.updated}</span>
              <span className="download-cell">
                <ButtonOutline label="Скачать" size="s" appearance="neutral" />
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">Демо-кейсы (для защиты)</h3>
            <p className="panel-hint">Готовые наборы: 25–35 ручных + автотесты для UI калькулятора и API Compute</p>
          </div>
        </div>

        <div className="table-wrapper">
          <div className="table-head cases-head">
            <span>ID</span>
            <span>Тип</span>
            <span>Описание</span>
            <span>Статус</span>
            <span />
          </div>
          {demoCases.map((row) => (
            <div key={row.id} className="table-row cases-row">
              <span>{row.id}</span>
              <span>DEMO</span>
              <span className="ellipsis">{row.title}</span>
              <span>{row.updated}</span>
              <span className="download-cell">
                <ButtonOutline label="Скачать" size="s" appearance="neutral" />
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

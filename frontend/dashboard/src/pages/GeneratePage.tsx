import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateTestCase } from '../api/testGeneration'
import { parseOpenAPI, ParseOpenAPIResponse } from '../api/parser'
import { ButtonFilled } from '@snack-uikit/button'
import { Card } from '@snack-uikit/card'
import { Alert } from '@snack-uikit/alert'
import './GeneratePage.css'

export function GeneratePage() {
  const navigate = useNavigate()
  const [description, setDescription] = useState('')
  const [testType, setTestType] = useState('manual')
  const [feature, setFeature] = useState('')
  const [story, setStory] = useState('')
  const [priority, setPriority] = useState('NORMAL')
  const [owner, setOwner] = useState('')
  const [jiraLink, setJiraLink] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [parsing, setParsing] = useState(false)
  const [parsedSpec, setParsedSpec] = useState<ParseOpenAPIResponse | null>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      setParsing(true)
      setError(null)
      try {
        const spec = await parseOpenAPI(selectedFile)
        setParsedSpec(spec)
        if (spec.info?.description) {
          setDescription(spec.info.description)
        }
        // Формируем описание из эндпоинтов
        if (spec.endpoints && spec.endpoints.length > 0) {
          const endpointsDesc = spec.endpoints
            .map((ep) => `${ep.method} ${ep.path}${ep.summary ? ` - ${ep.summary}` : ''}`)
            .join('\n')
          setDescription((prev) => (prev ? `${prev}\n\nЭндпоинты:\n${endpointsDesc}` : `Эндпоинты:\n${endpointsDesc}`))
        }
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || err.message || 'Не удалось распарсить файл OpenAPI'
        setError(`Ошибка парсинга: ${errorMsg}`)
        setFile(null)
        setParsedSpec(null)
      } finally {
        setParsing(false)
      }
    }
    // Сбрасываем значение input, чтобы можно было выбрать тот же файл снова
    e.target.value = ''
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) {
      setError('Пожалуйста, введите описание')
      return
    }

    // Для UI тестов не требуется OpenAPI файл
    if (testType === 'ui' && file) {
      setFile(null)
      setParsedSpec(null)
    }

    setLoading(true)
    setError(null)

    try {
      // Формируем описание с учетом типа теста
      let finalDescription = description
      
      // Для API тестов добавляем информацию из OpenAPI если есть
      if (testType === 'api' && parsedSpec) {
        if (parsedSpec.endpoints && parsedSpec.endpoints.length > 0) {
          const endpointsInfo = parsedSpec.endpoints
            .map((ep) => `- ${ep.method} ${ep.path}${ep.summary ? `: ${ep.summary}` : ''}`)
            .join('\n')
          finalDescription = `${description}\n\nAPI Endpoints:\n${endpointsInfo}`
        }
      }

      const response = await generateTestCase({
        description: finalDescription,
        test_type: testType,
        feature: feature || undefined,
        story: story || undefined,
        priority,
        owner: owner || undefined,
        jira_link: jiraLink || undefined,
      })
      navigate(`/tasks/${response.task_id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Не удалось сгенерировать тест-кейс')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="generate-page">
      <div className="page-header">
        <h1>Генерация тест-кейсов</h1>
        <p>Загрузите OpenAPI/YAML/JSON или опишите требования текстом — мы разберём и сгенерируем тесты</p>
      </div>

      <div className="generate-container">
        <Card>
          <form onSubmit={handleSubmit} className="generate-form">
            <div className="form-section">
              <h3>Конфигурация теста</h3>
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="testType">Тип теста *</label>
                  <select
                    id="testType"
                    value={testType}
                    onChange={(e) => {
                      const newType = e.target.value
                      setTestType(newType)
                      // Очищаем файл при смене типа теста с API на другой
                      if (newType !== 'api' && file) {
                        setFile(null)
                        setParsedSpec(null)
                      }
                    }}
                    required
                  >
                    <option value="manual">Ручной тест</option>
                    <option value="api">API тест</option>
                    <option value="ui">UI тест</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="priority">Приоритет</label>
                  <select
                    id="priority"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value="CRITICAL">Критический</option>
                    <option value="NORMAL">Обычный</option>
                    <option value="LOW">Низкий</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="feature">Фича</label>
                  <input
                    id="feature"
                    type="text"
                    value={feature}
                    onChange={(e) => setFeature(e.target.value)}
                    placeholder="например, Управление пользователями"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="story">История</label>
                  <input
                    id="story"
                    type="text"
                    value={story}
                    onChange={(e) => setStory(e.target.value)}
                    placeholder="например, Регистрация пользователя"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="owner">Владелец</label>
                  <input
                    id="owner"
                    type="text"
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                    placeholder="QA команда"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="jiraLink">Ссылка на JIRA</label>
                  <input
                    id="jiraLink"
                    type="url"
                    value={jiraLink}
                    onChange={(e) => setJiraLink(e.target.value)}
                    placeholder="https://jira.example.com/TICKET-123"
                  />
                </div>
              </div>
            </div>

            <div className="form-section">
              <h3>Входные данные</h3>
              {testType === 'api' && (
                <div className="form-group">
                  <label htmlFor="file">Загрузить спецификацию OpenAPI (необязательно)</label>
                  <div className={`upload-zone ${parsing ? 'disabled' : ''}`}>
                    <div className="upload-content" onClick={() => {
                      if (!parsing) {
                        const fileInput = document.getElementById('file') as HTMLInputElement
                        fileInput?.click()
                      }
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span className="upload-icon">📄</span>
                        <div className="upload-text">
                          <strong>{file ? file.name : 'Перетащите файл или выберите'}</strong>
                          <span>Поддерживаем .yaml / .yml / .json</span>
                        </div>
                      </div>
                      <ButtonFilled 
                        label="Выбрать файл" 
                        size="s" 
                        disabled={parsing}
                        onClick={(e) => {
                          e.stopPropagation()
                          if (!parsing) {
                            const fileInput = document.getElementById('file') as HTMLInputElement
                            fileInput?.click()
                          }
                        }}
                      />
                    </div>
                  </div>
                  <input
                    id="file"
                    type="file"
                    accept=".yaml,.yml,.json"
                    onChange={handleFileChange}
                    disabled={parsing}
                    className="hidden-input"
                  />
                  {parsing && <p className="parsing-status">Парсинг файла OpenAPI...</p>}
                  {file && !parsing && parsedSpec && (
                    <div className="file-info">
                      <p>✓ Выбран: {file.name}</p>
                      <p>
                        Эндпоинтов: {parsedSpec.endpoints?.length || 0} · Схем: {Object.keys(parsedSpec.schemas || {}).length}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="form-group">
                <label htmlFor="description">Описание / Требования *</label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Введите описание тест-кейса, требования или детали API эндпоинта..."
                  rows={12}
                  required
                />
              </div>
            </div>

            {error && (
              <Alert appearance="error" title="Ошибка" description={error} />
            )}

            <ButtonFilled
              type="submit"
              label={loading ? 'Генерация...' : 'Сгенерировать тест-кейс'}
              disabled={loading || !description.trim()}
              loading={loading}
              size="l"
            />
          </form>
        </Card>
      </div>
    </div>
  )
}

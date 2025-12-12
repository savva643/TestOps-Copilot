import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateTestCase } from '../api/testGeneration'
import { parseOpenAPI, ParseOpenAPIResponse } from '../api/parser'
import { generateAndCommitTests, validateGitLabToken, GitLabValidateResponse } from '../api/gitlabIntegration'
import { getStoredGitLabCredentials, storeGitLabCredentials } from '../api/auth'
import { ButtonFilled, ButtonOutline } from '@snack-uikit/button'
import { Card } from '@snack-uikit/card'
import { Alert } from '@snack-uikit/alert'
import { Divider } from '@snack-uikit/divider'
import './GeneratePage.css'

type TabType = 'manual' | 'gitlab'

export function GeneratePage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabType>('manual')
  
  // Manual generation state
  const [description, setDescription] = useState('')
  const [testType, setTestType] = useState('manual')
  const [feature, setFeature] = useState('')
  const [story, setStory] = useState('')
  const [priority, setPriority] = useState('NORMAL')
  const [owner, setOwner] = useState('')
  const [jiraLink, setJiraLink] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [parsing, setParsing] = useState(false)
  const [parsedSpec, setParsedSpec] = useState<ParseOpenAPIResponse | null>(null)
  
  // GitLab state
  const [gitlabUrl, setGitlabUrl] = useState('')
  const [gitlabToken, setGitlabToken] = useState('')
  const [gitlabBaseUrl, setGitlabBaseUrl] = useState('https://gitlab.com/api/v4')
  const [specPath, setSpecPath] = useState('')
  const [targetBranch, setTargetBranch] = useState('main')
  const [createMR, setCreateMR] = useState(true)
  const [validatingToken, setValidatingToken] = useState(false)
  const [tokenValid, setTokenValid] = useState<GitLabValidateResponse | null>(null)
  const [gitlabTestType, setGitlabTestType] = useState('api')
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Загружаем сохраненные GitLab credentials при монтировании
  useEffect(() => {
    const gitlabCreds = getStoredGitLabCredentials()
    if (gitlabCreds) {
      setGitlabToken(gitlabCreds.token)
      setGitlabBaseUrl(gitlabCreds.url)
      if (gitlabCreds.user) {
        setTokenValid({ valid: true, user_info: { username: gitlabCreds.user, id: 0, name: gitlabCreds.user, email: '' } })
      }
    }
  }, [])

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
    e.target.value = ''
  }

  const handleValidateGitLabToken = async () => {
    if (!gitlabToken.trim()) {
      setError('Введите GitLab токен')
      return
    }

    setValidatingToken(true)
    setError(null)
    try {
      const result = await validateGitLabToken({
        private_token: gitlabToken,
        gitlab_base_url: gitlabBaseUrl,
      })
      setTokenValid(result)
      if (result.valid && result.user_info) {
        // Сохраняем credentials
        storeGitLabCredentials(gitlabToken, gitlabBaseUrl, result.user_info.username)
      } else {
        setError(result.error || 'Токен недействителен')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Не удалось проверить токен')
      setTokenValid({ valid: false, error: 'Ошибка проверки' })
    } finally {
      setValidatingToken(false)
    }
  }

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) {
      setError('Пожалуйста, введите описание')
      return
    }

    if (testType === 'ui' && file) {
      setFile(null)
      setParsedSpec(null)
    }

    setLoading(true)
    setError(null)

    try {
      let finalDescription = description
      
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

  const handleGitLabSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!gitlabUrl.trim() || !specPath.trim()) {
      setError('Заполните GitLab URL и путь к спецификации')
      return
    }

    if (!tokenValid?.valid) {
      setError('Сначала проверьте GitLab токен')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const result = await generateAndCommitTests({
        gitlab_url: gitlabUrl,
        spec_path: specPath,
        test_type: gitlabTestType as 'api' | 'ui' | 'manual',
        target_branch: targetBranch,
        create_mr: createMR,
        private_token: gitlabToken,
        gitlab_base_url: gitlabBaseUrl,
        user_email: tokenValid.user_info?.email,
        user_name: tokenValid.user_info?.name,
      })

      if (result.success) {
        // Создаем задачу в БД через core-agent-service для отображения в истории
        try {
          const { createApiClient } = await import('../api/client')
          const api = createApiClient()
          await api.post('/api/v1/gitlab/task', {
            gitlab_url: gitlabUrl,
            spec_path: specPath,
            test_type: gitlabTestType,
            merge_request_url: result.merge_request_url,
            branch: result.branch,
            generated_files: result.generated_files,
            coverage_summary: result.coverage_summary,
          })
        } catch (taskErr) {
          // Игнорируем ошибку сохранения задачи, главное что MR создан
          console.warn('Failed to save GitLab task to history', taskErr)
        }

        if (result.merge_request_url) {
          alert(`Тесты успешно сгенерированы и закоммичены!\n\nMerge Request: ${result.merge_request_url}\nВетка: ${result.branch}\nФайлов: ${result.generated_files.length}`)
          navigate('/tasks')
        } else {
          alert(`Тесты успешно сгенерированы и закоммичены!\n\nВетка: ${result.branch}\nФайлов: ${result.generated_files.length}`)
          navigate('/tasks')
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Не удалось сгенерировать и закоммитить тесты')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="generate-page">
      <div className="page-header">
        <h1>Генерация тест-кейсов</h1>
        <p>
          Ручная генерация или автоматическая через GitLab репозиторий
        </p>
      </div>

      <Divider />

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'manual' ? 'active' : ''}`}
          onClick={() => setActiveTab('manual')}
          type="button"
        >
          Ручной
        </button>
        <button
          className={`tab-button ${activeTab === 'gitlab' ? 'active' : ''}`}
          onClick={() => setActiveTab('gitlab')}
          type="button"
        >
          GitLab
        </button>
      </div>

      <div className="generate-container">
        <Card>
          {error && (
            <div style={{ marginBottom: '1rem' }}>
              <Alert appearance="error" title="Ошибка" description={error} />
            </div>
          )}

          <div className={`tab-content ${activeTab === 'manual' ? 'tab-active' : 'tab-inactive'}`}>
          {activeTab === 'manual' && (
            <form onSubmit={handleManualSubmit} className="generate-form">
              <div className="form-section">
                <div style={{ marginBottom: '1rem' }}>
                  <h2>
                    Конфигурация теста
                  </h2>
                </div>
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="testType">Тип теста *</label>
                    <select
                      id="testType"
                      value={testType}
                      onChange={(e) => {
                        const newType = e.target.value
                        setTestType(newType)
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
                    <select id="priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
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
                <div style={{ marginBottom: '1rem' }}>
                  <h2>
                    Входные данные
                  </h2>
                </div>
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

              <ButtonFilled
                type="submit"
                label={loading ? 'Генерация...' : 'Сгенерировать тест-кейс'}
                disabled={loading || !description.trim()}
                loading={loading}
                size="l"
              />
            </form>
          )}

          </div>
          <div className={`tab-content ${activeTab === 'gitlab' ? 'tab-active' : 'tab-inactive'}`}>
          {activeTab === 'gitlab' && (
            <form onSubmit={handleGitLabSubmit} className="generate-form">
              <div className="form-section">
                <h2 style={{ marginBottom: '1rem' }}>
                  Подключение к GitLab
                </h2>

                <div className="form-group">
                  <label>GitLab Personal Access Token *</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="password"
                      className="form-input"
                      value={gitlabToken}
                      onChange={(e) => setGitlabToken(e.target.value)}
                      placeholder="glpat-xxxxxxxxxxxxxxxxxxxx"
                      disabled={loading || validatingToken}
                      style={{ flex: 1 }}
                    />
                    <ButtonOutline
                      label={validatingToken ? 'Проверка...' : 'Проверить'}
                      onClick={handleValidateGitLabToken}
                      disabled={!gitlabToken.trim() || validatingToken || loading}
                      size="s"
                    />
                  </div>
                  {tokenValid && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                      {tokenValid.valid ? (
                        <span style={{ color: '#10b981' }}>
                          ✓ Токен действителен {tokenValid.user_info?.username && `(${tokenValid.user_info.username})`}
                        </span>
                      ) : (
                        <span style={{ color: '#ef4444' }}>✗ Токен недействителен</span>
                      )}
                    </div>
                  )}
                  <p style={{ marginTop: '0.5rem', display: 'block' }}>
                    Создайте токен в GitLab: Settings → Access Tokens → Personal Access Tokens
                  </p>
                </div>

                <div className="form-group">
                  <label>GitLab API URL (опционально)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={gitlabBaseUrl}
                    onChange={(e) => setGitlabBaseUrl(e.target.value)}
                    placeholder="https://gitlab.com/api/v4"
                    disabled={loading}
                  />
                </div>
              </div>

              <div style={{ margin: '1.5rem 0' }}>
                <Divider />
              </div>

              <div className="form-section">
                <div style={{ marginBottom: '1rem' }}>
                  <h2>Параметры генерации</h2>
                </div>

                <div className="form-group">
                  <label>GitLab URL проекта *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={gitlabUrl}
                    onChange={(e) => setGitlabUrl(e.target.value)}
                    placeholder="https://gitlab.com/group/project"
                    disabled={loading}
                  />
                </div>

                <div className="form-group">
                  <label>Путь к спецификации в репозитории *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={specPath}
                    onChange={(e) => setSpecPath(e.target.value)}
                    placeholder="docs/openapi.yaml или openapi/compute.yaml"
                    disabled={loading}
                  />
                </div>

                <div className="form-group">
                  <label>Тип тестов</label>
                  <select
                    className="form-input"
                    value={gitlabTestType}
                    onChange={(e) => setGitlabTestType(e.target.value)}
                    disabled={loading}
                  >
                    <option value="api">API тесты</option>
                    <option value="ui">UI тесты</option>
                    <option value="manual">Ручные тесты</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Целевая ветка для MR</label>
                  <input
                    type="text"
                    className="form-input"
                    value={targetBranch}
                    onChange={(e) => setTargetBranch(e.target.value)}
                    placeholder="main"
                    disabled={loading}
                  />
                </div>

                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={createMR}
                      onChange={(e) => setCreateMR(e.target.checked)}
                      style={{ width: 'auto' }}
                    />
                    <span>Создать Merge Request</span>
                  </label>
                </div>
              </div>

              <ButtonFilled
                type="submit"
                label={loading ? 'Генерация и коммит в GitLab...' : 'Сгенерировать и закоммитить в GitLab'}
                disabled={
                  loading ||
                  !gitlabUrl.trim() ||
                  !specPath.trim() ||
                  !gitlabToken.trim() ||
                  !tokenValid?.valid
                }
                loading={loading}
                size="l"
              />
            </form>
          )}
          </div>
        </Card>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { Card } from '@snack-uikit/card'
import { Divider } from '@snack-uikit/divider'
import { ButtonFilled, ButtonOutline } from '@snack-uikit/button'
import { Alert } from '@snack-uikit/alert'
import { storeGitLabToken, getGitLabProjects, GitLabProject } from '../api/gitlab'
import {
  analyzeCoverage,
  findDuplicates,
  getOptimizationRecommendations,
  CoverageAnalysisResponse,
  DuplicateAnalysisResponse,
  OptimizationRecommendationsResponse,
} from '../api/optimizer'
import './OptimizePage.css'

type AnalysisStep = 'gitlab-setup' | 'project-select' | 'analyzing' | 'results'

export function OptimizePage() {
  const [step, setStep] = useState<AnalysisStep>('gitlab-setup')
  const [gitlabToken, setGitlabToken] = useState('')
  const [gitlabUrl, setGitlabUrl] = useState('https://gitlab.com')
  const [projects, setProjects] = useState<GitLabProject[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [branch, setBranch] = useState('main')
  const [testDirectory, setTestDirectory] = useState('tests')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [coverageResult, setCoverageResult] = useState<CoverageAnalysisResponse | null>(null)
  const [duplicatesResult, setDuplicatesResult] = useState<DuplicateAnalysisResponse | null>(null)
  const [recommendations, setRecommendations] = useState<OptimizationRecommendationsResponse | null>(null)

  // Загружаем сохраненный токен при монтировании
  useEffect(() => {
    const savedToken = localStorage.getItem('gitlab_token')
    const savedUrl = localStorage.getItem('gitlab_url')
    if (savedToken) {
      setGitlabToken(savedToken)
      if (savedUrl) {
        setGitlabUrl(savedUrl)
      }
      setStep('project-select')
      loadProjects(savedToken, savedUrl || 'https://gitlab.com')
    }
  }, [])

  const loadProjects = async (token: string, url: string) => {
    setLoading(true)
    setError(null)
    try {
      const projs = await getGitLabProjects(token, url)
      setProjects(projs)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Не удалось загрузить проекты')
      setStep('gitlab-setup')
    } finally {
      setLoading(false)
    }
  }

  const handleConnectGitLab = async () => {
    if (!gitlabToken.trim()) {
      setError('Введите GitLab токен')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await storeGitLabToken(gitlabToken, gitlabUrl)
      localStorage.setItem('gitlab_token', gitlabToken)
      localStorage.setItem('gitlab_url', gitlabUrl)
      await loadProjects(gitlabToken, gitlabUrl)
      setStep('project-select')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Не удалось подключиться к GitLab')
    } finally {
      setLoading(false)
    }
  }

  const validateRepository = async () => {
    if (!selectedProject || !gitlabToken) {
      return false
    }

    try {
      // Используем API для валидации репозитория
      const { createApiClient } = await import('../api/client')
      const api = createApiClient()
      const baseUrl = gitlabUrl.replace(/\/$/, '')
      const apiBaseUrl = baseUrl.includes('api/v4') ? baseUrl : `${baseUrl}/api/v4`
      
      const response = await api.get(`/api/v1/gitlab/project/${encodeURIComponent(selectedProject)}/tree`, {
        params: { ref: branch, recursive: false },
        headers: {
          'X-GitLab-Token': gitlabToken,
          'X-GitLab-URL': apiBaseUrl,
        },
      })
      
      return response.data && Array.isArray(response.data.files)
    } catch (err: any) {
      console.error('Repository validation failed', err)
      return false
    }
  }

  const handleAnalyze = async () => {
    if (!selectedProject) {
      setError('Выберите проект')
      return
    }

    // Валидируем репозиторий перед анализом
    const isValid = await validateRepository()
    if (!isValid) {
      setError('Не удалось получить доступ к репозиторию. Проверьте токен и путь к проекту.')
      return
    }

    setLoading(true)
    setError(null)
    setStep('analyzing')
    setCoverageResult(null)
    setDuplicatesResult(null)
    setRecommendations(null)

    try {
      // Запускаем все анализы параллельно
      const [coverage, duplicates, recs] = await Promise.all([
        analyzeCoverage(
          {
            gitlab_project_id: selectedProject,
            gitlab_url: gitlabUrl,
            branch,
            test_directory: testDirectory,
          },
          gitlabToken
        ),
        findDuplicates(
          {
            gitlab_project_id: selectedProject,
            gitlab_url: gitlabUrl,
            branch,
            test_directory: testDirectory,
            similarity_threshold: 0.8,
          },
          gitlabToken
        ),
        getOptimizationRecommendations(
          {
            gitlab_project_id: selectedProject,
            gitlab_url: gitlabUrl,
            branch,
            test_directory: testDirectory,
          },
          gitlabToken
        ),
      ])

      setCoverageResult(coverage)
      setDuplicatesResult(duplicates)
      setRecommendations(recs)
      setStep('results')
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Не удалось выполнить анализ')
      setStep('project-select')
    } finally {
      setLoading(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return '#ef4444'
      case 'medium':
        return '#f59e0b'
      case 'low':
        return '#10b981'
      default:
        return '#6b7280'
    }
  }

  return (
    <div className="optimize-page">
      <div className="page-header">
        <h1>Оптимизация тестов</h1>
        <p>Анализ покрытия тестами и поиск дубликатов в GitLab репозиториях</p>
      </div>

      <Divider />
      <div style={{ marginTop: '1.5rem' }}></div>

      {error && (
        <Alert
          appearance="error"
          title="Ошибка"
          description={error}
          onClose={() => setError(null)}
          className="optimize-alert"
        />
      )}

      {step === 'gitlab-setup' && (
        <Card className="optimize-card">
          <h2 className="card-title">Подключение к GitLab</h2>
          <p className="card-description">
            Введите ваш GitLab Personal Access Token для доступа к репозиториям. Токен должен иметь права на чтение
            репозиториев.
          </p>

          <div className="form-group">
            <label>
              <p>GitLab URL (опционально)</p>
            </label>
            <input
              type="text"
              className="form-input"
              value={gitlabUrl}
              onChange={(e) => setGitlabUrl(e.target.value)}
              placeholder="https://gitlab.com"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>
              <p>GitLab Personal Access Token *</p>
            </label>
            <input
              type="password"
              className="form-input"
              value={gitlabToken}
              onChange={(e) => setGitlabToken(e.target.value)}
              placeholder="glpat-xxxxxxxxxxxxxxxxxxxx"
              disabled={loading}
            />
            <p className="hint-text">
              Создайте токен в GitLab: Settings → Access Tokens → Personal Access Tokens
            </p>
          </div>

          <ButtonFilled 
            label={loading ? 'Подключение...' : 'Подключиться к GitLab'}
            onClick={handleConnectGitLab} 
            disabled={loading || !gitlabToken.trim()}
          />
        </Card>
      )}

      {step === 'project-select' && (
        <Card className="optimize-card">
          <div className="card-header">
            <h2>Выбор проекта</h2>
            <ButtonOutline label="Изменить токен" onClick={() => setStep('gitlab-setup')} />
          </div>

          <div className="form-group">
            <label>
              <p>Проект *</p>
            </label>
            <select
              className="form-input"
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              disabled={loading}
            >
              <option value="">Выберите проект...</option>
              {projects.map((project) => (
                <option key={project.id} value={project.path_with_namespace}>
                  {project.name} ({project.path_with_namespace})
                </option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>
                <p>Ветка</p>
              </label>
              <input
                type="text"
                className="form-input"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="main"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label>
                <p>Директория с тестами</p>
              </label>
              <input
                type="text"
                className="form-input"
                value={testDirectory}
                onChange={(e) => setTestDirectory(e.target.value)}
                placeholder="tests"
                disabled={loading}
              />
            </div>
          </div>

          <ButtonFilled 
            label={loading ? 'Анализ...' : 'Запустить анализ'}
            onClick={handleAnalyze} 
            disabled={loading || !selectedProject}
          />
        </Card>
      )}

      {step === 'analyzing' && (
        <Card className="optimize-card">
          <div className="analyzing-container">
            <div className="spinner"></div>
            <h2>Анализ в процессе...</h2>
            <p>Клонирование репозитория, анализ тестов и генерация отчетов</p>
          </div>
        </Card>
      )}

      {step === 'results' && (
        <div className="results-container">
          {/* Coverage Results */}
          {coverageResult && (
            <Card className="result-card">
              <h2 className="card-title">Анализ покрытия</h2>
              <Divider />
              <div className="coverage-stats">
                <div className="stat-item">
                  <p className="stat-value">
                    {coverageResult.coverage_percentage.toFixed(1)}%
                  </p>
                  <p>Покрытие тестами</p>
                </div>
                <div className="stat-item">
                  <p className="stat-value">
                    {coverageResult.test_files_analyzed}
                  </p>
                  <p>Файлов проанализировано</p>
                </div>
                <div className="stat-item">
                  <p className="stat-value">
                    {coverageResult.total_test_functions}
                  </p>
                  <p>Тест-функций</p>
                </div>
                <div className="stat-item">
                  <p className="stat-value">
                    {coverageResult.total_endpoints}
                  </p>
                  <p>Всего эндпоинтов</p>
                </div>
              </div>

              {coverageResult.uncovered_endpoints.length > 0 && (
                <div className="uncovered-section">
                  <p className="section-title">
                    Непокрытые эндпоинты ({coverageResult.uncovered_endpoints.length}):
                  </p>
                  <ul className="endpoints-list">
                    {coverageResult.uncovered_endpoints.slice(0, 10).map((endpoint, idx) => (
                      <li key={idx}>
                        <p>{endpoint}</p>
                      </li>
                    ))}
                    {coverageResult.uncovered_endpoints.length > 10 && (
                      <li>
                        <p>... и еще {coverageResult.uncovered_endpoints.length - 10}</p>
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </Card>
          )}

          {/* Duplicates Results */}
          {duplicatesResult && (
            <Card className="result-card">
              <h2 className="card-title">Поиск дубликатов</h2>
              <Divider />
              <div className="duplicates-stats">
                <p>
                  Найдено дубликатов: <strong>{duplicatesResult.duplicate_count}</strong>
                </p>
                <p>
                  Всего тестов: {duplicatesResult.total_tests}
                </p>
              </div>

              {duplicatesResult.duplicates.length > 0 && (
                <div className="duplicates-list">
                  {duplicatesResult.duplicates.slice(0, 5).map((dup, idx) => (
                    <div key={idx} className="duplicate-item">
                      <p>
                        <strong>{dup.test1}</strong>
                      </p>
                      <p>
                        <strong>{dup.test2}</strong>
                      </p>
                      <p style={{ color: dup.similarity > 0.9 ? '#ef4444' : '#f59e0b' }}>
                        Схожесть: {(dup.similarity * 100).toFixed(0)}% ({dup.method})
                      </p>
                    </div>
                  ))}
                  {duplicatesResult.duplicates.length > 5 && (
                    <p>
                      ... и еще {duplicatesResult.duplicates.length - 5} дубликатов
                    </p>
                  )}
                </div>
              )}
            </Card>
          )}

          {/* Recommendations */}
          {recommendations && (
            <Card className="result-card">
              <h2 className="card-title">Рекомендации по оптимизации</h2>
              <Divider />

              {recommendations.recommendations.length > 0 && (
                <div className="recommendations-section">
                  <p className="section-title">
                    Рекомендации:
                  </p>
                  {recommendations.recommendations.map((rec, idx) => (
                    <div key={idx} className="recommendation-item">
                      <div
                        className="priority-badge"
                        style={{ backgroundColor: getPriorityColor(rec.priority) }}
                      >
                        {rec.priority}
                      </div>
                      <div className="recommendation-content">
                        <p>
                          {rec.message}
                        </p>
                        <p className="action-text">
                          {rec.action}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {recommendations.best_practices.length > 0 && (
                <div className="best-practices-section">
                  <p className="section-title">
                    Лучшие практики:
                  </p>
                  <ul className="practices-list">
                    {recommendations.best_practices.map((practice, idx) => (
                      <li key={idx}>
                        <p>
                          {practice.message}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

          <div className="actions-footer">
            <ButtonOutline label="Новый анализ" onClick={() => setStep('project-select')} />
          </div>
        </div>
      )}
    </div>
  )
}

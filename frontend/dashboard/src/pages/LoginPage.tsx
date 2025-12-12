import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Card } from '@snack-uikit/card'
import { ButtonFilled, ButtonOutline } from '@snack-uikit/button'
import { Alert } from '@snack-uikit/alert'
import { Divider } from '@snack-uikit/divider'
import './AuthPage.css'
import { fetchIamToken, storeCredentials, storeToken, getStoredCredentials, clearCredentials, getStoredToken, getStoredGitLabCredentials, clearGitLabCredentials } from '../api/auth'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const isTestMode = useMemo(() => new URLSearchParams(location.search).get('test') !== null, [location.search])
  const appVersion = import.meta.env.VITE_APP_VERSION || 'v1.0.0'
  const [apiKeyId, setApiKeyId] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [gitlabCreds, setGitlabCreds] = useState<{ user: string; url: string } | null>(null)

  // Функция для маскировки чувствительных данных
  const maskSensitiveData = (value: string, showFirst: number = 4, showLast: number = 4): string => {
    if (!value || value.length <= showFirst + showLast) {
      return '•'.repeat(8)
    }
    const first = value.substring(0, showFirst)
    const last = value.substring(value.length - showLast)
    const masked = '•'.repeat(Math.max(8, value.length - showFirst - showLast))
    return `${first}${masked}${last}`
  }

  useEffect(() => {
    const credentials = getStoredCredentials()
    if (credentials) {
      setIsAuthenticated(true)
      setApiKeyId(credentials.keyId)
      setApiSecret(credentials.secret)
      if (credentials.llmApiKey) {
        setLlmApiKey(credentials.llmApiKey)
      }
      const token = getStoredToken()
      if (token) {
        setAccessToken(token)
      }
    }
    const gitlabCreds = getStoredGitLabCredentials()
    if (gitlabCreds) {
      setGitlabCreds({ user: gitlabCreds.user || '', url: gitlabCreds.url })
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await fetchIamToken(apiKeyId, apiSecret)
      if (data?.access_token) {
        storeCredentials(apiKeyId, apiSecret, llmApiKey || undefined)
        storeToken(data.access_token)
        setIsAuthenticated(true)
        navigate('/')
      } else {
        setError('Токен не получен, проверьте ключи.')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Не удалось получить токен')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    clearCredentials()
    setIsAuthenticated(false)
    setApiKeyId('')
    setApiSecret('')
    navigate('/')
  }

  const handleGitLabLogout = () => {
    clearGitLabCredentials()
    setGitlabCreds(null)
  }

  if (isAuthenticated) {
    return (
      <div className="auth-page">
        <div className="auth-header">
          <h1>Профиль</h1>
          <p className="helper">
            Информация о сохранённых ключах и токенах
          </p>
        </div>

        <div className="auth-container">
          <Card className="auth-card">
            <div className="vertical-gap">
              <div className="profile-info">
                <div className="profile-field" style={{ background: 'var(--surface-secondary)', padding: '12px', borderRadius: '12px' }}>
                  <p className="field-label">Версия приложения</p>
                  <p className="field-value">TestOps Copilot — {appVersion}</p>
                  <p className="helper" style={{ marginTop: '4px' }}>
                    Разработано командой Сваровски. Репозиторий:{' '}
                    <a href="https://github.com/savva643/TestOps-Copilot" target="_blank" rel="noreferrer">
                      github.com/savva643/TestOps-Copilot
                    </a>
                  </p>
                </div>

                <div className="profile-field">
                  <p className="field-label">
                    Key ID (IAM)
                  </p>
                  <p className="field-value">
                    {apiKeyId}
                  </p>
                </div>

                <div className="profile-field">
                  <p className="field-label">
                    Key Secret (IAM)
                  </p>
                  <p className="field-value">
                    {maskSensitiveData(apiSecret)}
                  </p>
                </div>

                {llmApiKey && (
                  <div className="profile-field">
                    <p className="field-label">
                      API Key (Cloud.ru Evolution Model)
                    </p>
                    <p className="field-value">
                      {maskSensitiveData(llmApiKey)}
                    </p>
                  </div>
                )}

                {accessToken && (
                  <div className="profile-field">
                    <p className="field-label">
                      Access Token (IAM)
                    </p>
                    <p className="field-value">
                      {maskSensitiveData(accessToken, 10, 10)}
                    </p>
                    <p className="helper">
                      Токен автоматически обновляется при необходимости
                    </p>
                  </div>
                )}

                {gitlabCreds && (
                  <div className="profile-field">
                    <p className="field-label">
                      GitLab подключение
                    </p>
                    <p className="field-value">
                      {gitlabCreds.user || 'Подключено'}
                    </p>
                    <p className="helper">
                      URL: {gitlabCreds.url}
                    </p>
                    <div style={{ marginTop: '0.5rem' }}>
                      <ButtonOutline
                        label="Отключить GitLab"
                        onClick={handleGitLabLogout}
                        size="s"
                        appearance="destructive"
                      />
                    </div>
                  </div>
                )}
              </div>

              <Divider />

              <p className="helper">
                Полная инструкция по аутентификации:{' '}
                <a
                  href="https://cloud.ru/docs/virtual-machines/ug/topics/api-ref__authentication?source-platform=Evolution"
                  target="_blank"
                  rel="noreferrer"
                >
                  Cloud.ru API Authentication
                </a>
              </p>

              <ButtonFilled
                label="Выйти"
                onClick={handleLogout}
                size="m"
                appearance="destructive"
                fullWidth
              />
            </div>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-header">
        <h1>Вход по сервисному ключу</h1>
        <p className="helper">
          Используйте сервисный ключ Cloud.ru для доступа к системе
        </p>
      </div>

      <div className="auth-container">
        <Card className="auth-card">
          <form onSubmit={handleSubmit} className="vertical-gap">
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="apiKeyId">Key ID (IAM)</label>
                <input
                  id="apiKeyId"
                  value={apiKeyId}
                  onChange={(e) => setApiKeyId(e.target.value)}
                  placeholder="Введите Key ID"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="apiSecret">Key Secret (IAM)</label>
                <input
                  id="apiSecret"
                  type="password"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  placeholder="Введите Key Secret"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="llmApiKey">API Key (Cloud.ru Evolution Model)</label>
                <input
                  id="llmApiKey"
                  type="password"
                  value={llmApiKey}
                  onChange={(e) => setLlmApiKey(e.target.value)}
                  placeholder="Введите API ключ для модели (не ограничен)"
                  required
                />
                <p className="helper">
                  API ключ для доступа к Cloud.ru Evolution Foundation Model
                </p>
              </div>
            </div>

            <p className="helper">
              Полная инструкция по получению ключей:{' '}
              <a
                href="https://cloud.ru/docs/virtual-machines/ug/topics/api-ref__authentication?source-platform=Evolution"
                target="_blank"
                rel="noreferrer"
              >
                Cloud.ru API Authentication
              </a>
            </p>

            <ButtonFilled
              type="submit"
              label={loading ? 'Получаем...' : 'Войти'}
              size="m"
              loading={loading}
              disabled={loading}
            />
            {isTestMode && (
              <ButtonOutline
                type="button"
                label="Использовать тестовый аккаунт"
                size="m"
                onClick={() => {
                  // Демо-значения из localStorage, предоставленные пользователем
                  setApiKeyId('e8cd3a5243f933a1b9721d4d35c2582c')
                  setApiSecret('7ef9e95ae8c9a163df949f0cc2bdc4c5')
                  setLlmApiKey('ZWI0ZDcwMDUtYmJhMS00OWUyLWEwNWYtZTYxNjliZjZlNTVh.0db2e453d4aa678fba26ea79fcbaa469')
                }}
              />
            )}

            {error && (
              <Alert
                appearance="error"
                title="Ошибка"
                description={typeof error === 'string' ? error : 'Не удалось получить токен'}
              />
            )}
          </form>
        </Card>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { ButtonFilled, ButtonOutlined } from '@snack-uikit/button'
import { Alert } from '@snack-uikit/alert'
import { Divider } from '@snack-uikit/divider'
import './AuthPage.css'
import { fetchIamToken, storeCredentials, storeToken, getStoredCredentials, clearCredentials, getStoredToken, getStoredGitLabCredentials, clearGitLabCredentials } from '../api/auth'

export function LoginPage() {
  const navigate = useNavigate()
  const [apiKeyId, setApiKeyId] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

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

  if (isAuthenticated) {
    return (
      <div className="auth-page">
        <div className="auth-header">
          <Typography family="sans" purpose="title" size="l">Профиль</Typography>
          <Typography family="sans" purpose="body" size="m" className="helper">
            Информация о сохранённых ключах и токенах
          </Typography>
        </div>

        <div className="auth-container">
          <Card className="auth-card">
            <div className="vertical-gap">
              <div className="profile-info">
                <div className="profile-field">
                  <Typography family="sans" purpose="body" size="s" className="field-label">
                    Key ID (IAM)
                  </Typography>
                  <Typography family="sans" purpose="body" size="m" className="field-value">
                    {apiKeyId}
                  </Typography>
                </div>

                <div className="profile-field">
                  <Typography family="sans" purpose="body" size="s" className="field-label">
                    Key Secret (IAM)
                  </Typography>
                  <Typography family="sans" purpose="body" size="m" className="field-value">
                    {maskSensitiveData(apiSecret)}
                  </Typography>
                </div>

                {llmApiKey && (
                  <div className="profile-field">
                    <Typography family="sans" purpose="body" size="s" className="field-label">
                      API Key (Cloud.ru Evolution Model)
                    </Typography>
                    <Typography family="sans" purpose="body" size="m" className="field-value">
                      {maskSensitiveData(llmApiKey)}
                    </Typography>
                  </div>
                )}

                {accessToken && (
                  <div className="profile-field">
                    <Typography family="sans" purpose="body" size="s" className="field-label">
                      Access Token (IAM)
                    </Typography>
                    <Typography family="sans" purpose="body" size="m" className="field-value">
                      {maskSensitiveData(accessToken, 10, 10)}
                    </Typography>
                    <Typography family="sans" purpose="body" size="s" className="helper">
                      Токен автоматически обновляется при необходимости
                    </Typography>
                  </div>
                )}

                {gitlabCreds && (
                  <div className="profile-field">
                    <Typography family="sans" purpose="body" size="s" className="field-label">
                      GitLab подключение
                    </Typography>
                    <Typography family="sans" purpose="body" size="m" className="field-value">
                      {gitlabCreds.user || 'Подключено'}
                    </Typography>
                    <Typography family="sans" purpose="body" size="s" className="helper">
                      URL: {gitlabCreds.url}
                    </Typography>
                    <ButtonOutlined
                      label="Отключить GitLab"
                      onClick={handleGitLabLogout}
                      size="s"
                      appearance="destructive"
                      style={{ marginTop: '0.5rem' }}
                    />
                  </div>
                )}
              </div>

              <Divider />

              <Typography family="sans" purpose="body" size="s" className="helper">
                Полная инструкция по аутентификации:{' '}
                <a
                  href="https://cloud.ru/docs/virtual-machines/ug/topics/api-ref__authentication?source-platform=Evolution"
                  target="_blank"
                  rel="noreferrer"
                >
                  Cloud.ru API Authentication
                </a>
              </Typography>

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
        <Typography family="sans" purpose="title" size="l">Вход по сервисному ключу</Typography>
        <Typography family="sans" purpose="body" size="m" className="helper">
          Используйте сервисный ключ Cloud.ru для доступа к системе
        </Typography>
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
                <Typography family="sans" purpose="body" size="s" className="helper">
                  API ключ для доступа к Cloud.ru Evolution Foundation Model
                </Typography>
              </div>
            </div>

            <Typography family="sans" purpose="body" size="s" className="helper">
              Полная инструкция по получению ключей:{' '}
              <a
                href="https://cloud.ru/docs/virtual-machines/ug/topics/api-ref__authentication?source-platform=Evolution"
                target="_blank"
                rel="noreferrer"
              >
                Cloud.ru API Authentication
              </a>
            </Typography>

            <ButtonFilled
              type="submit"
              label={loading ? 'Получаем...' : 'Войти'}
              size="m"
              loading={loading}
              disabled={loading}
            />

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

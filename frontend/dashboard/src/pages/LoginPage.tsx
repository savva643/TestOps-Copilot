import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Card } from '@snack-uikit/card'
import { ButtonFilled, ButtonOutline } from '@snack-uikit/button'
import { Alert } from '@snack-uikit/alert'
import './AuthPage.css'
import { fetchIamToken, storeCredentials, storeToken, getStoredCredentials } from '../api/auth'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const isTestMode = useMemo(() => new URLSearchParams(location.search).get('test') !== null, [location.search])
  const [apiKeyId, setApiKeyId] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    const credentials = getStoredCredentials()
    if (credentials) {
      setIsAuthenticated(true)
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

  // Если пользователь уже авторизован, перенаправляем на профиль
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/profile')
    }
  }, [isAuthenticated, navigate])

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

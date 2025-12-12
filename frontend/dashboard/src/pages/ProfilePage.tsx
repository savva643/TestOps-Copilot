import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card } from '@snack-uikit/card'
import { ButtonFilled, ButtonOutline } from '@snack-uikit/button'
import { Divider } from '@snack-uikit/divider'
import './AuthPage.css'
import { clearCredentials, getStoredCredentials, getStoredToken, getStoredGitLabCredentials, clearGitLabCredentials } from '../api/auth'

export function ProfilePage() {
  const navigate = useNavigate()
  const appVersion = import.meta.env.VITE_APP_VERSION || 'v1.0.0'
  const [apiKeyId, setApiKeyId] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [llmApiKey, setLlmApiKey] = useState('')
  const [accessToken, setAccessToken] = useState<string | null>(null)
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
      setApiKeyId(credentials.keyId)
      setApiSecret(credentials.secret)
      if (credentials.llmApiKey) {
        setLlmApiKey(credentials.llmApiKey)
      }
      const token = getStoredToken()
      if (token) {
        setAccessToken(token)
      }
    } else {
      // Если нет учетных данных, перенаправляем на страницу входа
      navigate('/login')
    }
    const gitlabCreds = getStoredGitLabCredentials()
    if (gitlabCreds) {
      setGitlabCreds({ user: gitlabCreds.user || '', url: gitlabCreds.url })
    }
  }, [navigate])

  const handleLogout = () => {
    clearCredentials()
    setApiKeyId('')
    setApiSecret('')
    navigate('/login')
  }

  const handleGitLabLogout = () => {
    clearGitLabCredentials()
    setGitlabCreds(null)
  }

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


import { useState } from 'react'
import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { ButtonFilled } from '@snack-uikit/button'
import { Alert } from '@snack-uikit/alert'
import './AuthPage.css'
import { fetchIamToken } from '../api/auth'

export function LoginPage() {
  const [apiKeyId, setApiKeyId] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [tokenSaved, setTokenSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setTokenSaved(false)
    setLoading(true)
    try {
      const data = await fetchIamToken(apiKeyId, apiSecret)
      if (data?.access_token) {
        localStorage.setItem('copilot_access_token', data.access_token)
        setTokenSaved(true)
      } else {
        setError('Токен не получен, проверьте ключи.')
      }
    } catch (err: any) {
      setError(err?.response?.data || err?.message || 'Не удалось получить токен')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-header">
        <Typography family="sans" purpose="title" size="l">Вход по сервисному ключу</Typography>
        <Typography family="sans" purpose="body" size="m" className="helper">
          Используйте сервисный ключ Cloud.ru. Токен будет получен по IAM API и передан в Authorization: Bearer.
        </Typography>
      </div>

      <div className="auth-container">
        <Card className="auth-card">
          <form onSubmit={handleSubmit} className="vertical-gap">
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="apiKeyId">Key ID</label>
                <input
                  id="apiKeyId"
                  value={apiKeyId}
                  onChange={(e) => setApiKeyId(e.target.value)}
                  placeholder="Введите Key ID"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="apiSecret">Key Secret</label>
                <input
                  id="apiSecret"
                  type="password"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  placeholder="Введите Key Secret"
                  required
                />
              </div>
            </div>

            <div className="vertical-gap">
              <Typography family="monospace" purpose="body" size="s" className="token-block">
{`curl --location 'https://iam.api.cloud.ru/api/v1/auth/token' \\
  --header 'Content-Type: application/json' \\
  --output token.json \\
  --data '{
    "keyId": "<key_id>",
    "secret": "<secret>"
  }'`}
              </Typography>
              <Typography family="sans" purpose="body" size="s" className="helper">
                После получения токена используйте заголовок: <strong>Authorization: Bearer $TOKEN</strong>
              </Typography>
              <Typography family="sans" purpose="body" size="s" className="helper">
                Полная инструкция: <a href="https://cloud.ru/docs/virtual-machines/ug/topics/api-ref__authentication?source-platform=Evolution" target="_blank" rel="noreferrer">Cloud.ru API Authentication</a>
              </Typography>
            </div>

            <ButtonFilled type="submit" label={loading ? 'Получаем...' : 'Получить и сохранить токен'} size="m" loading={loading} disabled={loading} />

            {tokenSaved && (
              <Alert
                appearance="success"
                title="Токен получен"
                description="access_token сохранён локально и будет использован в запросах."
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


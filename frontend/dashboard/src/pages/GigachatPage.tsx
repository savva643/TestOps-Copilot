import { Card } from '@snack-uikit/card'
import { Alert } from '@snack-uikit/alert'
import './TasksPage.css'

export function GigachatPage() {
  return (
    <div className="tasks-page">
      <div className="page-header">
        <h1>Гигачат</h1>
        <p>AI-ассистент для помощи в тестировании</p>
      </div>

      <div className="tasks-container">
        <Card>
          <Alert
            appearance="info"
            title="Скоро добавим Гигачат"
            description="Функционал Гигачата находится в разработке и будет доступен в ближайшее время."
          />
        </Card>
      </div>
    </div>
  )
}


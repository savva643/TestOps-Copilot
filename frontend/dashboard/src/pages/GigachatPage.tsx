import { Card } from '@snack-uikit/card'
import './GigachatPage.css'

export function GigachatPage() {
  return (
    <div className="gigachat-page">
      <div className="page-header">
        <h1>Гигачат</h1>
        <p>Скоро добавим гигчат</p>
      </div>

      <div className="gigachat-container">
        <Card>
          <div className="gigachat-placeholder">
            <h2>Скоро добавим гигчат</h2>
            <p>Функционал находится в разработке</p>
          </div>
        </Card>
      </div>
    </div>
  )
}

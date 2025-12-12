import { Card } from '@snack-uikit/card'
import { ButtonFilled } from '@snack-uikit/button'
import { Divider } from '@snack-uikit/divider'
import { Link } from 'react-router-dom'
import './HomePage.css'

export function HomePage() {
  return (
    <div className="home-page">
      <div className="hero">
        <h1>TestOps Copilot</h1>
        <p className="subtitle">
          AI-powered test generation and optimization platform
        </p>
        <div className="hero-actions">
          <Link to="/generate">
            <ButtonFilled label="Get Started" size="l" />
          </Link>
        </div>
      </div>

      <Divider />

      <div className="features-grid">
        <Card>
          <div className="feature-card">
            <div className="feature-icon">🧪</div>
            <h2>Generate Test Cases</h2>
            <p>
              Automatically generate comprehensive test cases from requirements
              and specifications using AI
            </p>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h2>Automated Tests</h2>
            <p>
              Create automated API and UI tests following best practices with
              Allure TestOps format
            </p>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h2>Coverage Analysis</h2>
            <p>
              Analyze test coverage, identify gaps, and get recommendations for
              improvement
            </p>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <h2>Find Duplicates</h2>
            <p>
              Detect duplicate tests and optimize your test suite for better
              efficiency
            </p>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h2>Fast Generation</h2>
            <p>
              Generate test cases in seconds with Cloud.ru Evolution Foundation
              Model
            </p>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h2>Standards Compliant</h2>
            <p>
              All generated tests follow AAA pattern and Allure TestOps as Code
              standards
            </p>
          </div>
        </Card>
      </div>

      <Divider />

      <Card className="quick-start">
        <h1>Quick Start</h1>
        <ol>
          <li><p>Go to Generate Tests page</p></li>
          <li><p>Upload OpenAPI specification or enter description</p></li>
          <li><p>Select test type (Manual, API, or UI)</p></li>
          <li><p>Get generated test cases in seconds</p></li>
        </ol>
      </Card>
    </div>
  )
}

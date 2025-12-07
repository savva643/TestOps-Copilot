import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { ButtonFilled } from '@snack-uikit/button'
import { Link } from 'react-router-dom'
import './HomePage.css'

export function HomePage() {
  return (
    <div className="home-page">
      <div className="hero">
        <Typography variant="h1" size="xl">TestOps Copilot</Typography>
        <Typography variant="body" size="l" className="subtitle">
          AI-powered test generation and optimization platform
        </Typography>
        <div className="hero-actions">
          <Link to="/generate">
            <ButtonFilled label="Get Started" size="l" />
          </Link>
        </div>
      </div>

      <div className="features-grid">
        <Card>
          <div className="feature-card">
            <div className="feature-icon">🧪</div>
            <Typography variant="h3" size="m">Generate Test Cases</Typography>
            <Typography variant="body" size="m">
              Automatically generate comprehensive test cases from requirements
              and specifications using AI
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <Typography variant="h3" size="m">Automated Tests</Typography>
            <Typography variant="body" size="m">
              Create automated API and UI tests following best practices with
              Allure TestOps format
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <Typography variant="h3" size="m">Coverage Analysis</Typography>
            <Typography variant="body" size="m">
              Analyze test coverage, identify gaps, and get recommendations for
              improvement
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <Typography variant="h3" size="m">Find Duplicates</Typography>
            <Typography variant="body" size="m">
              Detect duplicate tests and optimize your test suite for better
              efficiency
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <Typography variant="h3" size="m">Fast Generation</Typography>
            <Typography variant="body" size="m">
              Generate test cases in seconds with Cloud.ru Evolution Foundation
              Model
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <Typography variant="h3" size="m">Standards Compliant</Typography>
            <Typography variant="body" size="m">
              All generated tests follow AAA pattern and Allure TestOps as Code
              standards
            </Typography>
          </div>
        </Card>
      </div>

      <Card className="quick-start">
        <Typography variant="h2" size="l">Quick Start</Typography>
        <ol>
          <li>Go to Generate Tests page</li>
          <li>Upload OpenAPI specification or enter description</li>
          <li>Select test type (Manual, API, or UI)</li>
          <li>Get generated test cases in seconds</li>
        </ol>
      </Card>
    </div>
  )
}

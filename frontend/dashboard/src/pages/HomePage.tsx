import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { ButtonFilled } from '@snack-uikit/button'
import { Divider } from '@snack-uikit/divider'
import { Link } from 'react-router-dom'
import './HomePage.css'

export function HomePage() {
  return (
    <div className="home-page">
      <div className="hero">
        <Typography family="system" purpose="title" size="l">TestOps Copilot</Typography>
        <Typography family="system" purpose="body" size="l" className="subtitle">
          AI-powered test generation and optimization platform
        </Typography>
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
            <Typography family="system" purpose="title" size="m">Generate Test Cases</Typography>
            <Typography family="system" purpose="body" size="m">
              Automatically generate comprehensive test cases from requirements
              and specifications using AI
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <Typography family="system" purpose="title" size="m">Automated Tests</Typography>
            <Typography family="system" purpose="body" size="m">
              Create automated API and UI tests following best practices with
              Allure TestOps format
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <Typography family="system" purpose="title" size="m">Coverage Analysis</Typography>
            <Typography family="system" purpose="body" size="m">
              Analyze test coverage, identify gaps, and get recommendations for
              improvement
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <Typography family="system" purpose="title" size="m">Find Duplicates</Typography>
            <Typography family="system" purpose="body" size="m">
              Detect duplicate tests and optimize your test suite for better
              efficiency
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <Typography family="system" purpose="title" size="m">Fast Generation</Typography>
            <Typography family="system" purpose="body" size="m">
              Generate test cases in seconds with Cloud.ru Evolution Foundation
              Model
            </Typography>
          </div>
        </Card>

        <Card>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <Typography family="system" purpose="title" size="m">Standards Compliant</Typography>
            <Typography family="system" purpose="body" size="m">
              All generated tests follow AAA pattern and Allure TestOps as Code
              standards
            </Typography>
          </div>
        </Card>
      </div>

      <Divider />

      <Card className="quick-start">
        <Typography family="system" purpose="title" size="l">Quick Start</Typography>
        <ol>
          <li><Typography family="system" purpose="body" size="m">Go to Generate Tests page</Typography></li>
          <li><Typography family="system" purpose="body" size="m">Upload OpenAPI specification or enter description</Typography></li>
          <li><Typography family="system" purpose="body" size="m">Select test type (Manual, API, or UI)</Typography></li>
          <li><Typography family="system" purpose="body" size="m">Get generated test cases in seconds</Typography></li>
        </ol>
      </Card>
    </div>
  )
}

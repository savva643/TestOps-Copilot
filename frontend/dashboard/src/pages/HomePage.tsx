import './HomePage.css'

export function HomePage() {
  return (
    <div className="home-page">
      <div className="hero">
        <h1>TestOps Copilot</h1>
        <p className="subtitle">
          AI-powered test generation and optimization platform
        </p>
      </div>

      <div className="features-grid">
        <div className="feature-card">
          <div className="feature-icon">🧪</div>
          <h3>Generate Test Cases</h3>
          <p>
            Automatically generate comprehensive test cases from requirements
            and specifications using AI
          </p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🤖</div>
          <h3>Automated Tests</h3>
          <p>
            Create automated API and UI tests following best practices with
            Allure TestOps format
          </p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <h3>Coverage Analysis</h3>
          <p>
            Analyze test coverage, identify gaps, and get recommendations for
            improvement
          </p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🔍</div>
          <h3>Find Duplicates</h3>
          <p>
            Detect duplicate tests and optimize your test suite for better
            efficiency
          </p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">⚡</div>
          <h3>Fast Generation</h3>
          <p>
            Generate test cases in seconds with Cloud.ru Evolution Foundation
            Model
          </p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🎯</div>
          <h3>Standards Compliant</h3>
          <p>
            All generated tests follow AAA pattern and Allure TestOps as Code
            standards
          </p>
        </div>
      </div>

      <div className="quick-start">
        <h2>Quick Start</h2>
        <ol>
          <li>Go to Generate Tests page</li>
          <li>Upload OpenAPI specification or enter description</li>
          <li>Select test type (Manual, API, or UI)</li>
          <li>Get generated test cases in seconds</li>
        </ol>
      </div>
    </div>
  )
}

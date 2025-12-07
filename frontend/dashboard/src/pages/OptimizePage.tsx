import './OptimizePage.css'

export function OptimizePage() {
  return (
    <div className="optimize-page">
      <div className="page-header">
        <h1>Test Optimization</h1>
        <p>Analyze test coverage and find duplicates</p>
      </div>

      <div className="coming-soon">
        <div className="coming-soon-icon">🚀</div>
        <h2>Coming Soon in v1.1</h2>
        <p>
          This feature will allow you to:
        </p>
        <ul className="features-list">
          <li>Analyze test coverage for your Git repositories</li>
          <li>Find duplicate tests automatically</li>
          <li>Get recommendations for test optimization</li>
          <li>View coverage reports and metrics</li>
          <li>Integrate with GitLab for automated analysis</li>
        </ul>
      </div>
    </div>
  )
}

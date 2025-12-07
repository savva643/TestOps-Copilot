import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import './OptimizePage.css'

export function OptimizePage() {
  return (
    <div className="optimize-page">
      <div className="page-header">
        <Typography variant="h1" size="xl">Test Optimization</Typography>
        <Typography variant="body" size="m">Analyze test coverage and find duplicates</Typography>
      </div>

      <Card className="coming-soon">
        <div className="coming-soon-icon">🚀</div>
        <Typography variant="h2" size="l">Coming Soon in v1.1</Typography>
        <Typography variant="body" size="m">
          This feature will allow you to:
        </Typography>
        <ul className="features-list">
          <li><Typography variant="body" size="m">Analyze test coverage for your Git repositories</Typography></li>
          <li><Typography variant="body" size="m">Find duplicate tests automatically</Typography></li>
          <li><Typography variant="body" size="m">Get recommendations for test optimization</Typography></li>
          <li><Typography variant="body" size="m">View coverage reports and metrics</Typography></li>
          <li><Typography variant="body" size="m">Integrate with GitLab for automated analysis</Typography></li>
        </ul>
      </Card>
    </div>
  )
}

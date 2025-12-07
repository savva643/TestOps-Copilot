import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { Divider } from '@snack-uikit/divider'
import './OptimizePage.css'

export function OptimizePage() {
  return (
    <div className="optimize-page">
      <div className="page-header">
        <Typography purpose="title" size="l">Test Optimization</Typography>
        <Typography purpose="body" size="m">Analyze test coverage and find duplicates</Typography>
      </div>

      <Divider />

      <Card className="coming-soon">
        <div className="coming-soon-icon">🚀</div>
        <Typography purpose="title" size="l">Coming Soon in v1.1</Typography>
        <Divider />
        <Typography purpose="body" size="m">
          This feature will allow you to:
        </Typography>
        <ul className="features-list">
          <li><Typography purpose="body" size="m">Analyze test coverage for your Git repositories</Typography></li>
          <li><Typography purpose="body" size="m">Find duplicate tests automatically</Typography></li>
          <li><Typography purpose="body" size="m">Get recommendations for test optimization</Typography></li>
          <li><Typography purpose="body" size="m">View coverage reports and metrics</Typography></li>
          <li><Typography purpose="body" size="m">Integrate with GitLab for automated analysis</Typography></li>
        </ul>
      </Card>
    </div>
  )
}

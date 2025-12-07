import { useState } from 'react'
import { generateTestCase } from '../api/testGeneration'
import { parseOpenAPI, ParseOpenAPIResponse } from '../api/parser'
import { ButtonFilled } from '@snack-uikit/button'
import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
// Using basic HTML inputs with snack-uikit styling for now
// Will update when snack-uikit packages are properly installed
import { Badge } from '@snack-uikit/badge'
import './GeneratePage.css'

export function GeneratePage() {
  const [description, setDescription] = useState('')
  const [testType, setTestType] = useState('manual')
  const [feature, setFeature] = useState('')
  const [story, setStory] = useState('')
  const [priority, setPriority] = useState('NORMAL')
  const [owner, setOwner] = useState('')
  const [jiraLink, setJiraLink] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [parsing, setParsing] = useState(false)
  const [parsedSpec, setParsedSpec] = useState<ParseOpenAPIResponse | null>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      setParsing(true)
      try {
        const spec = await parseOpenAPI(selectedFile)
        setParsedSpec(spec)
        if (spec.info?.description) {
          setDescription(spec.info.description)
        }
      } catch (err) {
        setError('Failed to parse OpenAPI file')
      } finally {
        setParsing(false)
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) {
      setError('Please enter a description')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await generateTestCase({
        description,
        test_type: testType,
        feature: feature || undefined,
        story: story || undefined,
        priority,
        owner: owner || undefined,
        jira_link: jiraLink || undefined,
      })
      setResult(response)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate test case')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="generate-page">
      <div className="page-header">
        <Typography variant="h1" size="xl">Generate Test Case</Typography>
        <Typography variant="body" size="m">
          Create test cases from requirements or OpenAPI specifications
        </Typography>
      </div>

      <div className="generate-container">
        <Card>
          <form onSubmit={handleSubmit} className="generate-form">
            <div className="form-section">
              <Typography variant="h3" size="m">Test Configuration</Typography>
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="testType">Test Type *</label>
                  <select
                    id="testType"
                    value={testType}
                    onChange={(e) => setTestType(e.target.value)}
                    required
                  >
                    <option value="manual">Manual Test</option>
                    <option value="api">API Test</option>
                    <option value="ui">UI Test</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="priority">Priority</label>
                  <select
                    id="priority"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="NORMAL">Normal</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="feature">Feature</label>
                  <input
                    id="feature"
                    type="text"
                    value={feature}
                    onChange={(e) => setFeature(e.target.value)}
                    placeholder="e.g., User Management"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="story">Story</label>
                  <input
                    id="story"
                    type="text"
                    value={story}
                    onChange={(e) => setStory(e.target.value)}
                    placeholder="e.g., User Registration"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="owner">Owner</label>
                  <input
                    id="owner"
                    type="text"
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                    placeholder="QA Team"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="jiraLink">JIRA Link</label>
                  <input
                    id="jiraLink"
                    type="url"
                    value={jiraLink}
                    onChange={(e) => setJiraLink(e.target.value)}
                    placeholder="https://jira.example.com/TICKET-123"
                  />
                </div>
              </div>
            </div>

            <div className="form-section">
              <Typography variant="h3" size="m">Input</Typography>
              <div className="form-group">
                <label htmlFor="file">Upload OpenAPI Specification (Optional)</label>
                <input
                  id="file"
                  type="file"
                  accept=".yaml,.yml,.json"
                  onChange={handleFileChange}
                  disabled={parsing}
                />
                {parsing && <Typography variant="body" size="s">Parsing OpenAPI file...</Typography>}
                {file && !parsing && (
                  <div className="file-info">
                    <Typography variant="body" size="s">✓ Selected: {file.name}</Typography>
                    {parsedSpec && (
                      <Typography variant="body" size="s">
                        Found {parsedSpec.endpoints?.length || 0} endpoints
                      </Typography>
                    )}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="description">Description / Requirements *</label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={12}
                  placeholder="Enter test case description, requirements, or API endpoint details..."
                  required
                />
              </div>
            </div>

            {error && (
              <Card className="error-card">
                <Typography variant="body" size="m" color="error">
                  <strong>Error:</strong> {error}
                </Typography>
              </Card>
            )}

            <ButtonFilled
              type="submit"
              label={loading ? 'Generating...' : 'Generate Test Case'}
              disabled={loading || !description.trim()}
              loading={loading}
              size="l"
            />
          </form>
        </Card>

        {result && (
          <Card className="result-section">
            <Typography variant="h3" size="m">Generation Result</Typography>
            <div className="result-header">
              <Badge label="Success" variant="success" />
              <Typography variant="body" size="m">Task ID: {result.task_id}</Typography>
            </div>
            <div className="result-content">
              <Typography variant="body" size="m">
                <strong>Status:</strong> {result.status}
              </Typography>
              <Typography variant="body" size="m">
                <strong>Message:</strong> {result.message}
              </Typography>
              <Typography variant="body" size="s" className="info-text">
                Check the Tasks page to see the generated test case when it's ready.
              </Typography>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

import { useState } from 'react'
import { generateTestCase } from '../api/testGeneration'
import { parseOpenAPI, ParseOpenAPIResponse } from '../api/parser'
import { ButtonFilled } from '@snack-uikit/button'
import { Card } from '@snack-uikit/card'
import { Typography } from '@snack-uikit/typography'
import { TextField, SelectField, TextareaField } from '@snack-uikit/fields'
import { Status } from '@snack-uikit/status'
import { Alert } from '@snack-uikit/alert'
import { Divider } from '@snack-uikit/divider'
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

      <Divider />

      <div className="generate-container">
        <Card>
          <form onSubmit={handleSubmit} className="generate-form">
            <div className="form-section">
              <Typography variant="h3" size="m">Test Configuration</Typography>
              <div className="form-grid">
                <SelectField
                  label="Test Type *"
                  value={testType}
                  onChange={(value) => setTestType(value)}
                  options={[
                    { value: 'manual', label: 'Manual Test' },
                    { value: 'api', label: 'API Test' },
                    { value: 'ui', label: 'UI Test' },
                  ]}
                  required
                />

                <SelectField
                  label="Priority"
                  value={priority}
                  onChange={(value) => setPriority(value)}
                  options={[
                    { value: 'CRITICAL', label: 'Critical' },
                    { value: 'NORMAL', label: 'Normal' },
                    { value: 'LOW', label: 'Low' },
                  ]}
                />

                <TextField
                  label="Feature"
                  value={feature}
                  onChange={(value) => setFeature(value)}
                  placeholder="e.g., User Management"
                />

                <TextField
                  label="Story"
                  value={story}
                  onChange={(value) => setStory(value)}
                  placeholder="e.g., User Registration"
                />

                <TextField
                  label="Owner"
                  value={owner}
                  onChange={(value) => setOwner(value)}
                  placeholder="QA Team"
                />

                <TextField
                  label="JIRA Link"
                  value={jiraLink}
                  onChange={(value) => setJiraLink(value)}
                  placeholder="https://jira.example.com/TICKET-123"
                  type="url"
                />
              </div>
            </div>

            <Divider />

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

              <TextareaField
                label="Description / Requirements *"
                value={description}
                onChange={(value) => setDescription(value)}
                placeholder="Enter test case description, requirements, or API endpoint details..."
                rows={12}
                required
              />
            </div>

            {error && (
              <Alert appearance="negative" title="Error" description={error} />
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
            <Divider />
            <div className="result-header">
              <Status label="Success" appearance="positive" />
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

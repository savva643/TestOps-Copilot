import { useState } from 'react'
import { generateTestCase } from '../api/testGeneration'
import { parseOpenAPI } from '../api/parser'
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      // TODO: Parse OpenAPI file and extract description
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
        <h1>Generate Test Case</h1>
        <p>Create test cases from requirements or OpenAPI specifications</p>
      </div>

      <div className="generate-container">
        <form onSubmit={handleSubmit} className="generate-form">
          <div className="form-section">
            <h3>Test Configuration</h3>
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
            <h3>Input</h3>
            <div className="form-group">
              <label htmlFor="file">Upload OpenAPI Specification (Optional)</label>
              <input
                id="file"
                type="file"
                accept=".yaml,.yml,.json"
                onChange={handleFileChange}
                disabled={parsing}
              />
              {parsing && <p className="file-info">Parsing OpenAPI file...</p>}
              {file && !parsing && (
                <div className="file-info">
                  <p>✓ Selected: {file.name}</p>
                  {parsedSpec && (
                    <p className="spec-info">
                      Found {parsedSpec.endpoints?.length || 0} endpoints
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="description">
                Description / Requirements *
              </label>
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
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          <button
            type="submit"
            className="submit-button"
            disabled={loading || !description.trim()}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Generating...
              </>
            ) : (
              'Generate Test Case'
            )}
          </button>
        </form>

        {result && (
          <div className="result-section">
            <h3>Generation Result</h3>
            <div className="result-card">
              <div className="result-header">
                <span className="status-badge success">Success</span>
                <span className="task-id">Task ID: {result.task_id}</span>
              </div>
              <div className="result-content">
                <p>
                  <strong>Status:</strong> {result.status}
                </p>
                <p>
                  <strong>Message:</strong> {result.message}
                </p>
                <p className="info-text">
                  Check the Tasks page to see the generated test case when it's
                  ready.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

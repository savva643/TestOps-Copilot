import { createApiClient } from './client'

const apiClient = createApiClient()

export interface GenerateTestCaseRequest {
  description: string
  test_type?: string
  feature?: string
  story?: string
  priority?: string
  owner?: string
  jira_link?: string
}

export async function generateTestCase(request: GenerateTestCaseRequest) {
  const response = await apiClient.post('/api/v1/generate/test-case', request)
  return response.data
}


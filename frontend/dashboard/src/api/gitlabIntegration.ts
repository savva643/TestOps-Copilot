import { createApiClient } from './client'

const api = createApiClient()

export interface GitLabGenerateRequest {
  gitlab_url: string
  spec_path: string
  test_type: 'api' | 'ui' | 'manual'
  branch?: string
  target_branch?: string
  create_mr?: boolean
  private_token: string
  gitlab_base_url?: string
  user_email?: string
  user_name?: string
  commit_message?: string
}

export interface GitLabGenerateResponse {
  success: boolean
  merge_request_url?: string
  branch: string
  commit_id?: string
  generated_files: string[]
  coverage_summary: {
    endpoints_covered: number
    tests_generated: number
    estimated_coverage: string
  }
}

export interface GitLabValidateRequest {
  private_token: string
  gitlab_base_url?: string
}

export interface GitLabValidateResponse {
  valid: boolean
  user_info?: {
    id: number
    username: string
    name: string
    email: string
  }
  error?: string
}

export async function validateGitLabToken(request: GitLabValidateRequest): Promise<GitLabValidateResponse> {
  const response = await api.post<GitLabValidateResponse>('/api/v1/gitlab/validate-token', request)
  return response.data
}

export async function generateAndCommitTests(request: GitLabGenerateRequest): Promise<GitLabGenerateResponse> {
  const response = await api.post<GitLabGenerateResponse>('/api/v1/gitlab/generate-and-commit', request, {
    timeout: 300000, // 5 minutes
  })
  return response.data
}





import { createApiClient } from './client'

const api = createApiClient()

export interface CoverageAnalysisRequest {
  git_repo_url?: string
  gitlab_project_id?: string
  gitlab_url?: string
  branch?: string
  test_directory?: string
  api_spec_path?: string
}

export interface CoverageAnalysisResponse {
  coverage_percentage: number
  covered_endpoints: string[]
  uncovered_endpoints: string[]
  recommendations: string[]
  test_files_analyzed: number
  total_test_functions: number
  total_endpoints: number
}

export interface DuplicateAnalysisRequest {
  git_repo_url?: string
  gitlab_project_id?: string
  gitlab_url?: string
  branch?: string
  test_directory?: string
  similarity_threshold?: number
}

export interface Duplicate {
  test1: string
  test2: string
  similarity: number
  method: string
}

export interface DuplicateAnalysisResponse {
  duplicates: Duplicate[]
  total_tests: number
  duplicate_count: number
}

export interface OptimizationRecommendation {
  type: string
  priority: string
  message: string
  action: string
}

export interface OptimizationRecommendationsResponse {
  recommendations: OptimizationRecommendation[]
  performance_issues: Array<{
    type: string
    message: string
    suggestion: string
  }>
  best_practices: Array<{
    type: string
    message: string
  }>
}

export async function analyzeCoverage(
  request: CoverageAnalysisRequest,
  gitlabToken?: string
): Promise<CoverageAnalysisResponse> {
  const headers: Record<string, string> = {}
  if (gitlabToken) {
    headers['X-GitLab-Token'] = gitlabToken
  }
  const response = await api.post<CoverageAnalysisResponse>(
    '/api/v1/optimize/coverage',
    request,
    { headers }
  )
  return response.data
}

export async function findDuplicates(
  request: DuplicateAnalysisRequest,
  gitlabToken?: string
): Promise<DuplicateAnalysisResponse> {
  const headers: Record<string, string> = {}
  if (gitlabToken) {
    headers['X-GitLab-Token'] = gitlabToken
  }
  const response = await api.post<DuplicateAnalysisResponse>(
    '/api/v1/optimize/duplicates',
    request,
    { headers }
  )
  return response.data
}

export async function getOptimizationRecommendations(
  request: CoverageAnalysisRequest,
  gitlabToken?: string
): Promise<OptimizationRecommendationsResponse> {
  const headers: Record<string, string> = {}
  if (gitlabToken) {
    headers['X-GitLab-Token'] = gitlabToken
  }
  const response = await api.post<OptimizationRecommendationsResponse>(
    '/api/v1/optimize/recommendations',
    request,
    { headers }
  )
  return response.data
}





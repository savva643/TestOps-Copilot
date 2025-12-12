import { createApiClient } from './client'

const api = createApiClient()

export interface GitLabProject {
  id: number
  name: string
  path_with_namespace: string
  web_url: string
  description?: string
}

export interface GitLabTokenRequest {
  gitlab_token: string
  gitlab_url?: string
}

export interface GitLabTokenResponse {
  status: string
  message: string
  user?: string
}

export async function storeGitLabToken(token: string, url?: string): Promise<GitLabTokenResponse> {
  const response = await api.post<GitLabTokenResponse>('/api/v1/auth/gitlab/token', {
    gitlab_token: token,
    gitlab_url: url,
  })
  return response.data
}

export async function getGitLabProjects(token: string, url?: string): Promise<GitLabProject[]> {
  const headers: Record<string, string> = {
    'X-GitLab-Token': token,
  }
  if (url) {
    headers['X-GitLab-URL'] = url
  }
  const response = await api.get<{ projects: GitLabProject[] }>('/api/v1/gitlab/projects', {
    headers,
  })
  return response.data.projects
}





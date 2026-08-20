import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema'

export type SessionRead = components['schemas']['SessionRead']
export type CurrentUserRead = components['schemas']['CurrentUserRead']
export type WorkspaceRead = components['schemas']['WorkspaceRead']
export type NavigationNodeRead = components['schemas']['NavigationNodeRead']
export type JarvisConfig = components['schemas']['JarvisConfig']
export type ProblemDetails = components['schemas']['ProblemDetails']

export class ApiProblem extends Error {
  readonly problem: ProblemDetails

  constructor(problem: ProblemDetails) {
    super(problem.detail)
    this.name = 'ApiProblem'
    this.problem = problem
  }
}

export class JarvisApiClient {
  private csrfToken: string | null = null
  private readonly baseUrl: string
  private readonly client: ReturnType<typeof createClient<paths>>

  constructor(baseUrl = '') {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.client = createClient<paths>({
      baseUrl: this.baseUrl,
      credentials: 'include',
    })
    const csrfMiddleware: Middleware = {
      onRequest: ({ request }) => {
        if (
          this.csrfToken &&
          !['GET', 'HEAD', 'OPTIONS'].includes(request.method.toUpperCase())
        ) {
          request.headers.set('X-CSRF-Token', this.csrfToken)
        }
        return request
      },
    }
    this.client.use(csrfMiddleware)
  }

  async session(): Promise<SessionRead> {
    const result = await this.client.GET('/api/v1/auth/session')
    const data = this.unwrap(result)
    this.csrfToken = data.csrfToken
    return data
  }

  async me(): Promise<CurrentUserRead> {
    return this.unwrap(await this.client.GET('/api/v1/me'))
  }

  async navigation(workspaceId: string): Promise<NavigationNodeRead[]> {
    return this.unwrap(
      await this.client.GET('/api/v1/workspaces/{workspace_id}/navigation', {
        params: { path: { workspace_id: workspaceId } },
      }),
    )
  }

  async exportConfiguration(workspaceId: string): Promise<JarvisConfig> {
    return this.unwrap(
      await this.client.GET(
        '/api/v1/workspaces/{workspace_id}/configuration/export',
        {
          params: { path: { workspace_id: workspaceId } },
        },
      ),
    )
  }

  async logout(): Promise<void> {
    const result = await this.client.POST('/api/v1/auth/logout', {
      params: {
        header: {
          'X-CSRF-Token': this.csrfToken ?? '',
        },
      },
    })
    if (result.error) {
      throw this.problem(result.error, result.response)
    }
    this.csrfToken = null
  }

  loginUrl(returnPath = '/'): string {
    const query = new URLSearchParams({ return_path: returnPath })
    return `${this.baseUrl}/api/v1/auth/login?${query.toString()}`
  }

  private unwrap<T>(result: {
    data?: T
    error?: unknown
    response: Response
  }): T {
    if (result.error || result.data === undefined) {
      throw this.problem(result.error, result.response)
    }
    return result.data
  }

  private problem(error: unknown, response: Response): Error {
    if (
      error &&
      typeof error === 'object' &&
      'code' in error &&
      'detail' in error &&
      'requestId' in error
    ) {
      return new ApiProblem(error as ProblemDetails)
    }
    return new Error(`JARVIS API request failed with status ${response.status}`)
  }
}


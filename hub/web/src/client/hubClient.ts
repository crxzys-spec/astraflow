import type { Ref } from 'vue'

export interface HubClient {
  requestJson: <T>(path: string, options?: RequestInit, requireAuth?: boolean) => Promise<T>
  requestAuth: <T>(path: string, body: Record<string, unknown>) => Promise<T>
}

export interface HubClientOptions {
  apiBase: Ref<string>
  authToken: Ref<string>
  storageKeyToken: string
}

function normalizeBase(base: string) {
  return base.replace(/\/$/, '')
}

export function createHubClient(options: HubClientOptions): HubClient {
  const { apiBase, authToken, storageKeyToken } = options

  async function requestJson<T>(
    path: string,
    options: RequestInit = {},
    requireAuth = false
  ): Promise<T> {
    const tokenValue =
      authToken.value.trim()
      || (localStorage.getItem(storageKeyToken) || '').trim()
    if (tokenValue && !authToken.value) {
      authToken.value = tokenValue
    }
    if (requireAuth && !tokenValue) {
      throw new Error('Token required to call hub API.')
    }
    const url = `${normalizeBase(apiBase.value)}${path}`
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
    if (tokenValue) {
      headers.set('Authorization', `Bearer ${tokenValue}`)
    }
    const response = await fetch(url, { ...options, headers })
    if (!response.ok) {
      const message = response.status === 401
        ? 'Unauthorized. Check your token.'
        : `Request failed (${response.status})`
      throw new Error(message)
    }
    if (response.status === 204) {
      return null as T
    }
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      return null as T
    }
    return (await response.json()) as T
  }

  async function requestAuth<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const url = `${normalizeBase(apiBase.value)}${path}`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(body)
    })
    if (!response.ok) {
      const message = response.status === 401
        ? 'Invalid credentials.'
        : response.status === 409
          ? 'Username already exists.'
          : `Request failed (${response.status})`
      throw new Error(message)
    }
    return (await response.json()) as T
  }

  return { requestJson, requestAuth }
}

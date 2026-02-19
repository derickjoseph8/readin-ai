/**
 * API Client with authentication support and retry logic
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us'

// Retry configuration
const MAX_RETRIES = 3
const INITIAL_RETRY_DELAY = 1000 // 1 second
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]

interface ApiError {
  message: string
  status: number
  retryable?: boolean
}

/**
 * Helper to delay execution with exponential backoff
 */
const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms))

/**
 * Calculate exponential backoff delay
 */
const getBackoffDelay = (attempt: number): number =>
  INITIAL_RETRY_DELAY * Math.pow(2, attempt)

class ApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('readin_token')
    }
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('readin_token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('readin_token')
    }
  }

  getToken(): string | null {
    return this.token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryCount: number = 0
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      })

      if (!response.ok) {
        const error: ApiError = {
          message: 'An error occurred',
          status: response.status,
          retryable: RETRYABLE_STATUS_CODES.includes(response.status),
        }

        try {
          const data = await response.json()
          error.message = data.detail || data.message || error.message
        } catch {
          // Ignore JSON parse errors
        }

        // Provide specific error messages based on status codes
        if (response.status === 401) {
          error.message = 'Your session has expired. Please log in again.'
          error.retryable = false
          this.clearToken()
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
        } else if (response.status === 403) {
          error.message = 'You do not have permission to perform this action.'
          error.retryable = false
        } else if (response.status === 429) {
          error.message = 'Too many requests. Please wait a moment and try again.'
          // 429 is retryable with backoff
        } else if (response.status >= 500) {
          error.message = 'Server error. Please try again later.'
          // 5xx errors are retryable
        }

        // Retry for transient failures
        if (error.retryable && retryCount < MAX_RETRIES) {
          const backoffDelay = getBackoffDelay(retryCount)
          await delay(backoffDelay)
          return this.request<T>(endpoint, options, retryCount + 1)
        }

        throw error
      }

      return response.json()
    } catch (err) {
      // Handle network errors (fetch failures)
      if (err instanceof TypeError && err.message.includes('fetch')) {
        const networkError: ApiError = {
          message: 'Network error. Please check your connection.',
          status: 0,
          retryable: true,
        }

        // Retry network errors
        if (retryCount < MAX_RETRIES) {
          const backoffDelay = getBackoffDelay(retryCount)
          await delay(backoffDelay)
          return this.request<T>(endpoint, options, retryCount + 1)
        }

        throw networkError
      }

      throw err
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()
export default apiClient

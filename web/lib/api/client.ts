/**
 * API Client with authentication support and retry logic
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us'

// Retry configuration
const MAX_RETRIES = 3
const INITIAL_RETRY_DELAY = 1000 // 1 second
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]

/**
 * Error type categorization for better error handling
 */
export enum ApiErrorType {
  NETWORK = 'NETWORK',           // Network connectivity issues
  AUTHENTICATION = 'AUTH',       // 401 - Session expired
  AUTHORIZATION = 'FORBIDDEN',   // 403 - Permission denied
  NOT_FOUND = 'NOT_FOUND',       // 404 - Resource not found
  VALIDATION = 'VALIDATION',     // 400/422 - Invalid input
  RATE_LIMIT = 'RATE_LIMIT',     // 429 - Too many requests
  SERVER = 'SERVER',             // 5xx - Server errors
  TIMEOUT = 'TIMEOUT',           // Request timeout
  UNKNOWN = 'UNKNOWN',           // Unknown error
}

export interface ApiError {
  message: string
  status: number
  retryable: boolean
  type: ApiErrorType
  originalError?: Error
}

/**
 * Helper to delay execution with exponential backoff
 */
const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms))

/**
 * Calculate exponential backoff delay with jitter
 */
const getBackoffDelay = (attempt: number): number => {
  const baseDelay = INITIAL_RETRY_DELAY * Math.pow(2, attempt)
  // Add random jitter (0-25% of base delay) to prevent thundering herd
  const jitter = Math.random() * 0.25 * baseDelay
  return baseDelay + jitter
}

/**
 * Determine error type from status code
 */
const getErrorType = (status: number): ApiErrorType => {
  if (status === 0) return ApiErrorType.NETWORK
  if (status === 401) return ApiErrorType.AUTHENTICATION
  if (status === 403) return ApiErrorType.AUTHORIZATION
  if (status === 404) return ApiErrorType.NOT_FOUND
  if (status === 400 || status === 422) return ApiErrorType.VALIDATION
  if (status === 408) return ApiErrorType.TIMEOUT
  if (status === 429) return ApiErrorType.RATE_LIMIT
  if (status >= 500) return ApiErrorType.SERVER
  return ApiErrorType.UNKNOWN
}

/**
 * Check if an error is a network error
 */
const isNetworkError = (err: unknown): boolean => {
  if (err instanceof TypeError) {
    const message = err.message.toLowerCase()
    return (
      message.includes('fetch') ||
      message.includes('network') ||
      message.includes('failed to fetch') ||
      message.includes('networkerror') ||
      message.includes('connection')
    )
  }
  // Handle AbortError (timeout)
  if (err instanceof DOMException && err.name === 'AbortError') {
    return true
  }
  return false
}

class ApiClient {
  private baseUrl: string
  private token: string | null = null
  // Track pending requests by URL+method to prevent duplicate in-flight requests
  private pendingRequests: Map<string, Promise<any>> = new Map()

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('readin_token')
    }
  }

  /**
   * Generate a unique key for a request based on URL and method
   */
  private getRequestKey(endpoint: string, method: string): string {
    return `${method}:${endpoint}`
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
    retryCount: number = 0,
    skipDedup: boolean = false
  ): Promise<T> {
    const method = options.method || 'GET'
    const requestKey = this.getRequestKey(endpoint, method)

    // For GET requests, deduplicate in-flight requests
    // Skip deduplication for retries to avoid promise conflicts
    if (method === 'GET' && !skipDedup && retryCount === 0) {
      const pendingRequest = this.pendingRequests.get(requestKey)
      if (pendingRequest) {
        // Return the existing in-flight request
        return pendingRequest as Promise<T>
      }
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`
    }

    // Create the request promise
    const requestPromise = (async (): Promise<T> => {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      })

      if (!response.ok) {
        const errorType = getErrorType(response.status)
        const error: ApiError = {
          message: 'An error occurred',
          status: response.status,
          retryable: RETRYABLE_STATUS_CODES.includes(response.status),
          type: errorType,
        }

        try {
          const data = await response.json()
          error.message = data.detail || data.message || error.message
        } catch {
          // Ignore JSON parse errors - use default message
        }

        // Provide specific error messages based on status codes
        switch (response.status) {
          case 400:
            error.message = error.message || 'Invalid request. Please check your input.'
            error.retryable = false
            break
          case 401:
            error.message = 'Your session has expired. Please log in again.'
            error.retryable = false
            this.clearToken()
            if (typeof window !== 'undefined') {
              window.location.href = '/login'
            }
            break
          case 403:
            error.message = error.message || 'You do not have permission to perform this action.'
            error.retryable = false
            break
          case 404:
            error.message = error.message || 'The requested resource was not found.'
            error.retryable = false
            break
          case 408:
            error.message = 'Request timed out. Please try again.'
            // Timeout is retryable
            break
          case 422:
            error.message = error.message || 'The provided data is invalid.'
            error.retryable = false
            break
          case 429:
            error.message = 'Too many requests. Please wait a moment and try again.'
            // 429 is retryable with backoff
            break
          case 500:
            error.message = 'Internal server error. Our team has been notified.'
            break
          case 502:
            error.message = 'Service temporarily unavailable. Please try again.'
            break
          case 503:
            error.message = 'Service is under maintenance. Please try again later.'
            break
          case 504:
            error.message = 'Gateway timeout. Please try again.'
            break
          default:
            if (response.status >= 500) {
              error.message = error.message || 'Server error. Please try again later.'
            }
        }

        // Retry for transient failures
        if (error.retryable && retryCount < MAX_RETRIES) {
          const backoffDelay = getBackoffDelay(retryCount)
          await delay(backoffDelay)
          return this.request<T>(endpoint, options, retryCount + 1, true)
        }

        throw error
      }

      return response.json()
    } catch (err) {
      // Handle network errors (fetch failures, timeouts, connection issues)
      if (isNetworkError(err)) {
        const isTimeout = err instanceof DOMException && err.name === 'AbortError'
        const networkError: ApiError = {
          message: isTimeout
            ? 'Request timed out. Please check your connection and try again.'
            : 'Network error. Please check your internet connection.',
          status: 0,
          retryable: true,
          type: isTimeout ? ApiErrorType.TIMEOUT : ApiErrorType.NETWORK,
          originalError: err instanceof Error ? err : undefined,
        }

        // Retry network errors with exponential backoff
        if (retryCount < MAX_RETRIES) {
          const backoffDelay = getBackoffDelay(retryCount)
          await delay(backoffDelay)
          return this.request<T>(endpoint, options, retryCount + 1, true)
        }

        // Update message to indicate all retries exhausted
        networkError.message = isTimeout
          ? 'Request timed out after multiple attempts. Please try again later.'
          : 'Unable to connect after multiple attempts. Please check your internet connection.'

        throw networkError
      }

      // Re-throw ApiErrors as-is
      if ((err as ApiError).type !== undefined) {
        throw err
      }

      // Wrap unknown errors
      const unknownError: ApiError = {
        message: err instanceof Error ? err.message : 'An unexpected error occurred',
        status: 0,
        retryable: false,
        type: ApiErrorType.UNKNOWN,
        originalError: err instanceof Error ? err : undefined,
      }
      throw unknownError
    }
    })()

    // Store the request promise for deduplication (only for GET requests on first attempt)
    if (method === 'GET' && retryCount === 0 && !skipDedup) {
      this.pendingRequests.set(requestKey, requestPromise)

      // Clean up the pending request when it completes (success or failure)
      requestPromise.finally(() => {
        this.pendingRequests.delete(requestKey)
      })
    }

    return requestPromise
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

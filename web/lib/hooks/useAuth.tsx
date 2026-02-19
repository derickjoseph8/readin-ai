'use client'

import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { authApi, User, UserStatus } from '../api/auth'
import apiClient from '../api/client'

interface AuthError {
  message: string
  code?: string
  retryable: boolean
}

interface AuthContextType {
  user: User | null
  status: UserStatus | null
  isLoading: boolean
  isAuthenticated: boolean
  token: string | null
  error: AuthError | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  refreshStatus: () => Promise<void>
  updateUser: (data: { full_name?: string; profession?: string; company?: string }) => Promise<void>
  retry: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

// Helper to create user-friendly error messages
function getErrorMessage(err: unknown): AuthError {
  if (err instanceof Error) {
    const message = err.message.toLowerCase()

    if (message.includes('network') || message.includes('fetch')) {
      return {
        message: 'Unable to connect to the server. Please check your internet connection.',
        code: 'NETWORK_ERROR',
        retryable: true
      }
    }

    if (message.includes('401') || message.includes('unauthorized')) {
      return {
        message: 'Your session has expired. Please log in again.',
        code: 'UNAUTHORIZED',
        retryable: false
      }
    }

    if (message.includes('403') || message.includes('forbidden')) {
      return {
        message: 'You do not have permission to perform this action.',
        code: 'FORBIDDEN',
        retryable: false
      }
    }

    if (message.includes('500') || message.includes('server')) {
      return {
        message: 'Something went wrong on our end. Please try again later.',
        code: 'SERVER_ERROR',
        retryable: true
      }
    }

    return {
      message: err.message,
      code: 'UNKNOWN',
      retryable: true
    }
  }

  return {
    message: 'An unexpected error occurred. Please try again.',
    code: 'UNKNOWN',
    retryable: true
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<UserStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<AuthError | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const MAX_RETRIES = 3

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const refreshStatus = useCallback(async () => {
    try {
      setError(null)
      const statusData = await authApi.getStatus()
      setUser(statusData.user)
      setStatus(statusData)
      setRetryCount(0)
    } catch (err) {
      const authError = getErrorMessage(err)
      setError(authError)
      setUser(null)
      setStatus(null)
    }
  }, [])

  const retry = useCallback(async () => {
    if (retryCount >= MAX_RETRIES) {
      setError({
        message: 'Maximum retry attempts reached. Please refresh the page.',
        code: 'MAX_RETRIES',
        retryable: false
      })
      return
    }

    setRetryCount(prev => prev + 1)
    setIsLoading(true)

    // Exponential backoff delay
    const delay = Math.min(1000 * Math.pow(2, retryCount), 10000)
    await new Promise(resolve => setTimeout(resolve, delay))

    if (authApi.isAuthenticated()) {
      await refreshStatus()
    }
    setIsLoading(false)
  }, [retryCount, refreshStatus])

  useEffect(() => {
    const checkAuth = async () => {
      if (authApi.isAuthenticated()) {
        await refreshStatus()
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [refreshStatus])

  const login = async (email: string, password: string) => {
    try {
      setError(null)
      const response = await authApi.login({ email, password })
      setUser(response.user)
      await refreshStatus()
    } catch (err) {
      const authError = getErrorMessage(err)
      // Customize login-specific error messages
      if (authError.code === 'UNAUTHORIZED') {
        authError.message = 'Invalid email or password. Please try again.'
      }
      setError(authError)
      throw err
    }
  }

  const register = async (email: string, password: string, fullName?: string) => {
    try {
      setError(null)
      const response = await authApi.register({ email, password, full_name: fullName })
      setUser(response.user)
      await refreshStatus()
    } catch (err) {
      const authError = getErrorMessage(err)
      setError(authError)
      throw err
    }
  }

  const logout = () => {
    authApi.logout()
    setUser(null)
    setStatus(null)
    setError(null)
    setRetryCount(0)
  }

  const updateUser = async (data: { full_name?: string; profession?: string; company?: string }) => {
    try {
      setError(null)
      const updatedUser = await authApi.updateProfile(data)
      setUser(updatedUser)
    } catch (err) {
      const authError = getErrorMessage(err)
      setError(authError)
      throw err
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        isLoading,
        isAuthenticated: !!user,
        token: apiClient.getToken(),
        error,
        login,
        register,
        logout,
        refreshStatus,
        updateUser,
        retry,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default useAuth

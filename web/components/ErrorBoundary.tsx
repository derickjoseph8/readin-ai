'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertCircle, RefreshCw, AlertTriangle, WifiOff } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  name?: string // Optional name for identifying which boundary caught the error
  onError?: (error: Error, errorInfo: ErrorInfo) => void // Optional callback for custom error handling
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
  retryCount: number
}

// Error classification helper
function classifyError(error: Error): {
  type: 'network' | 'auth' | 'render' | 'unknown'
  message: string
  retryable: boolean
} {
  const message = error.message.toLowerCase()

  if (message.includes('network') || message.includes('fetch') || message.includes('failed to fetch')) {
    return {
      type: 'network',
      message: 'Network connection issue. Please check your internet connection.',
      retryable: true
    }
  }

  if (message.includes('401') || message.includes('unauthorized') || message.includes('session')) {
    return {
      type: 'auth',
      message: 'Your session has expired. Please refresh the page to log in again.',
      retryable: false
    }
  }

  if (message.includes('chunk') || message.includes('loading') || message.includes('module')) {
    return {
      type: 'render',
      message: 'Failed to load component. This might be due to a network issue.',
      retryable: true
    }
  }

  return {
    type: 'unknown',
    message: 'Something went wrong. Please try again.',
    retryable: true
  }
}

export default class ErrorBoundary extends Component<Props, State> {
  private maxRetries = 3

  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, retryCount: 0 }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const boundaryName = this.props.name || 'Anonymous'

    // Log detailed error information
    console.error(`[ErrorBoundary: ${boundaryName}] Caught an error:`, {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack
      },
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString()
    })

    // Store error info for display
    this.setState({ errorInfo })

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // In production, you might want to send this to an error tracking service
    // Example: sendToErrorTracking({ error, errorInfo, boundaryName })
  }

  handleRetry = () => {
    const { retryCount } = this.state

    if (retryCount >= this.maxRetries) {
      console.warn(`[ErrorBoundary] Max retries (${this.maxRetries}) reached`)
      return
    }

    this.setState(prevState => ({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      retryCount: prevState.retryCount + 1
    }))
  }

  handleRefreshPage = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      const { error, retryCount } = this.state
      const classification = error ? classifyError(error) : { type: 'unknown', message: 'An error occurred', retryable: true }
      const canRetry = classification.retryable && retryCount < this.maxRetries

      // Select icon based on error type
      const IconComponent = classification.type === 'network' ? WifiOff :
                           classification.type === 'auth' ? AlertTriangle :
                           AlertCircle

      return (
        <div
          className="flex flex-col items-center justify-center p-6 sm:p-8 text-center bg-premium-surface/50 rounded-xl border border-premium-border"
          role="alert"
          aria-live="assertive"
        >
          <div className={`w-14 h-14 rounded-full flex items-center justify-center mb-4 ${
            classification.type === 'network' ? 'bg-yellow-500/20' :
            classification.type === 'auth' ? 'bg-orange-500/20' :
            'bg-red-500/20'
          }`}>
            <IconComponent className={`w-7 h-7 ${
              classification.type === 'network' ? 'text-yellow-400' :
              classification.type === 'auth' ? 'text-orange-400' :
              'text-red-400'
            }`} aria-hidden="true" />
          </div>

          <h2 className="text-lg sm:text-xl font-semibold text-white mb-2">
            {classification.type === 'network' ? 'Connection Issue' :
             classification.type === 'auth' ? 'Session Expired' :
             'Something went wrong'}
          </h2>

          <p className="text-gray-400 mb-4 text-sm sm:text-base max-w-md">
            {classification.message}
          </p>

          {/* Show retry count if retrying */}
          {retryCount > 0 && canRetry && (
            <p className="text-xs text-gray-500 mb-4">
              Retry attempt {retryCount} of {this.maxRetries}
            </p>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            {canRetry ? (
              <button
                onClick={this.handleRetry}
                className="flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all min-h-[44px] touch-manipulation"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                Try Again
              </button>
            ) : (
              <button
                onClick={this.handleRefreshPage}
                className="flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all min-h-[44px] touch-manipulation"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                Refresh Page
              </button>
            )}

            {/* Show refresh option even when retry is available, as secondary action */}
            {canRetry && (
              <button
                onClick={this.handleRefreshPage}
                className="flex items-center justify-center gap-2 px-5 py-2.5 bg-premium-surface text-gray-300 font-medium rounded-lg border border-premium-border hover:bg-premium-surface/80 transition-all min-h-[44px] touch-manipulation"
              >
                Refresh Page
              </button>
            )}
          </div>

          {/* Development mode: show error details */}
          {process.env.NODE_ENV === 'development' && error && (
            <details className="mt-6 w-full max-w-lg text-left">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
                Technical Details (Development Only)
              </summary>
              <div className="mt-2 p-3 bg-premium-bg rounded-lg text-xs font-mono overflow-auto max-h-40">
                <p className="text-red-400">{error.name}: {error.message}</p>
                {error.stack && (
                  <pre className="text-gray-500 mt-2 whitespace-pre-wrap text-[10px]">
                    {error.stack}
                  </pre>
                )}
              </div>
            </details>
          )}
        </div>
      )
    }

    return this.props.children
  }
}

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { meetingsApi, Meeting, MeetingDetail, MeetingStats } from '../api/meetings'

interface MeetingsError {
  message: string
  code?: string
  retryable: boolean
}

// Helper to create user-friendly error messages
function getErrorMessage(err: unknown, context: string): MeetingsError {
  if (err instanceof Error) {
    const message = err.message.toLowerCase()

    if (message.includes('network') || message.includes('fetch') || message.includes('failed to fetch')) {
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

    if (message.includes('404') || message.includes('not found')) {
      return {
        message: `The ${context} you're looking for could not be found.`,
        code: 'NOT_FOUND',
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

    if (message.includes('timeout')) {
      return {
        message: 'The request took too long. Please try again.',
        code: 'TIMEOUT',
        retryable: true
      }
    }

    return {
      message: `Failed to load ${context}. Please try again.`,
      code: 'UNKNOWN',
      retryable: true
    }
  }

  return {
    message: `An unexpected error occurred while loading ${context}.`,
    code: 'UNKNOWN',
    retryable: true
  }
}

// Helper for exponential backoff delay
function getBackoffDelay(retryCount: number): number {
  return Math.min(1000 * Math.pow(2, retryCount), 10000)
}

export function useMeetings(page = 1, perPage = 10) {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MeetingsError | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const MAX_RETRIES = 3
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true
    return () => { isMounted.current = false }
  }, [])

  const fetchMeetings = useCallback(async (isRetry = false) => {
    if (!isMounted.current) return

    setIsLoading(true)
    if (!isRetry) {
      setError(null)
      setRetryCount(0)
    }

    try {
      const response = await meetingsApi.list(page, perPage)
      if (isMounted.current) {
        setMeetings(response.meetings)
        setTotal(response.total)
        setError(null)
        setRetryCount(0)
      }
    } catch (err) {
      if (isMounted.current) {
        const meetingsError = getErrorMessage(err, 'meetings')
        setError(meetingsError)
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false)
      }
    }
  }, [page, perPage])

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

    // Exponential backoff delay
    const delay = getBackoffDelay(retryCount)
    await new Promise(resolve => setTimeout(resolve, delay))

    await fetchMeetings(true)
  }, [retryCount, fetchMeetings])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  useEffect(() => {
    fetchMeetings()
  }, [fetchMeetings])

  return {
    meetings,
    total,
    isLoading,
    error,
    refresh: fetchMeetings,
    retry,
    clearError,
    totalPages: Math.ceil(total / perPage),
  }
}

export function useMeeting(id: number | null) {
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MeetingsError | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const MAX_RETRIES = 3
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true
    return () => { isMounted.current = false }
  }, [])

  const fetchMeeting = useCallback(async (isRetry = false) => {
    if (!id || !isMounted.current) return

    setIsLoading(true)
    if (!isRetry) {
      setError(null)
      setRetryCount(0)
    }

    try {
      const data = await meetingsApi.get(id)
      if (isMounted.current) {
        setMeeting(data)
        setError(null)
        setRetryCount(0)
      }
    } catch (err) {
      if (isMounted.current) {
        const meetingError = getErrorMessage(err, 'meeting')
        setError(meetingError)
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false)
      }
    }
  }, [id])

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

    // Exponential backoff delay
    const delay = getBackoffDelay(retryCount)
    await new Promise(resolve => setTimeout(resolve, delay))

    await fetchMeeting(true)
  }, [retryCount, fetchMeeting])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  useEffect(() => {
    fetchMeeting()
  }, [fetchMeeting])

  return {
    meeting,
    isLoading,
    error,
    refresh: fetchMeeting,
    retry,
    clearError,
  }
}

export function useMeetingStats() {
  const [stats, setStats] = useState<MeetingStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MeetingsError | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const MAX_RETRIES = 3
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true
    return () => { isMounted.current = false }
  }, [])

  const fetchStats = useCallback(async (isRetry = false) => {
    if (!isMounted.current) return

    setIsLoading(true)
    if (!isRetry) {
      setError(null)
      setRetryCount(0)
    }

    try {
      const data = await meetingsApi.getStats()
      if (isMounted.current) {
        setStats(data)
        setError(null)
        setRetryCount(0)
      }
    } catch (err) {
      if (isMounted.current) {
        const statsError = getErrorMessage(err, 'statistics')
        setError(statsError)
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false)
      }
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

    // Exponential backoff delay
    const delay = getBackoffDelay(retryCount)
    await new Promise(resolve => setTimeout(resolve, delay))

    await fetchStats(true)
  }, [retryCount, fetchStats])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return { stats, isLoading, error, retry, clearError, refresh: fetchStats }
}

export default useMeetings

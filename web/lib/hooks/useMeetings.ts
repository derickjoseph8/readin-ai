'use client'

import { useState, useEffect, useCallback } from 'react'
import { meetingsApi, Meeting, MeetingDetail, MeetingStats } from '../api/meetings'

export function useMeetings(page = 1, perPage = 10) {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMeetings = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await meetingsApi.list(page, perPage)
      setMeetings(response.meetings)
      setTotal(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load meetings')
    } finally {
      setIsLoading(false)
    }
  }, [page, perPage])

  useEffect(() => {
    fetchMeetings()
  }, [fetchMeetings])

  return {
    meetings,
    total,
    isLoading,
    error,
    refresh: fetchMeetings,
    totalPages: Math.ceil(total / perPage),
  }
}

export function useMeeting(id: number | null) {
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMeeting = useCallback(async () => {
    if (!id) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await meetingsApi.get(id)
      setMeeting(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load meeting')
    } finally {
      setIsLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchMeeting()
  }, [fetchMeeting])

  return {
    meeting,
    isLoading,
    error,
    refresh: fetchMeeting,
  }
}

export function useMeetingStats() {
  const [stats, setStats] = useState<MeetingStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await meetingsApi.getStats()
        setStats(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load stats')
      } finally {
        setIsLoading(false)
      }
    }
    fetchStats()
  }, [])

  return { stats, isLoading, error }
}

export default useMeetings

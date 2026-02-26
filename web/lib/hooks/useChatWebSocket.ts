'use client'

import { useEffect, useRef, useCallback, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us'
const WS_URL = API_URL.replace('https://', 'wss://').replace('http://', 'ws://')

export type ChatEventType =
  | 'chat.connection_established'
  | 'chat.connection_error'
  | 'chat.new_message'
  | 'chat.message_read'
  | 'chat.typing_start'
  | 'chat.typing_stop'
  | 'chat.session_status_changed'
  | 'chat.agent_joined'
  | 'chat.agent_left'
  | 'chat.queue_position_update'
  | 'chat.session_ended'

export interface ChatWebSocketMessage {
  event: ChatEventType
  data: Record<string, unknown>
  timestamp: string
}

export interface UseChatWebSocketOptions {
  sessionId?: number | null
  onMessage?: (message: ChatWebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  enabled?: boolean
}

export function useChatWebSocket({
  sessionId,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  enabled = true,
}: UseChatWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  const getToken = useCallback(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('readin_token')
    }
    return null
  }, [])

  const connect = useCallback(() => {
    const token = getToken()
    if (!token || !enabled) return

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    try {
      const ws = new WebSocket(`${WS_URL}/api/v1/ws/chat?token=${token}`)

      ws.onopen = () => {
        setIsConnected(true)
        setConnectionError(null)
        onConnect?.()

        // If we have a session, join it
        if (sessionId) {
          ws.send(JSON.stringify({
            action: 'join_session',
            data: { session_id: sessionId }
          }))
        }
      }

      ws.onmessage = (event) => {
        try {
          const message: ChatWebSocketMessage = JSON.parse(event.data)
          onMessage?.(message)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        onDisconnect?.()

        // Attempt reconnect after 3 seconds
        if (enabled) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, 3000)
        }
      }

      ws.onerror = (error) => {
        setConnectionError('WebSocket connection error')
        onError?.(error)
      }

      wsRef.current = ws
    } catch (err) {
      setConnectionError('Failed to create WebSocket connection')
      console.error('WebSocket connection error:', err)
    }
  }, [enabled, sessionId, onConnect, onDisconnect, onMessage, onError, getToken])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((sessionId: number, message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'send_message',
        data: {
          session_id: sessionId,
          message,
          message_type: 'text'
        }
      }))
      return true
    }
    return false
  }, [])

  const sendTypingStart = useCallback((sessionId: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'typing_start',
        data: { session_id: sessionId }
      }))
    }
  }, [])

  const sendTypingStop = useCallback((sessionId: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'typing_stop',
        data: { session_id: sessionId }
      }))
    }
  }, [])

  const joinSession = useCallback((sessionId: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'join_session',
        data: { session_id: sessionId }
      }))
    }
  }, [])

  const leaveSession = useCallback((sessionId: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'leave_session',
        data: { session_id: sessionId }
      }))
    }
  }, [])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (enabled) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [enabled, connect, disconnect])

  // Join session when sessionId changes
  useEffect(() => {
    if (isConnected && sessionId) {
      joinSession(sessionId)
    }
  }, [isConnected, sessionId, joinSession])

  return {
    isConnected,
    connectionError,
    sendMessage,
    sendTypingStart,
    sendTypingStop,
    joinSession,
    leaveSession,
    connect,
    disconnect,
  }
}

'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  MessageSquare,
  X,
  Send,
  Minimize2,
  User,
  Shield,
  Clock,
  AlertCircle,
  Bot,
  UserCircle
} from 'lucide-react'
import { useMyChat } from '@/lib/hooks/useAdmin'
import { supportApi, ChatMessage } from '@/lib/api/admin'

type ChatStatus = 'idle' | 'waiting' | 'active' | 'ended'

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [chatStatus, setChatStatus] = useState<ChatStatus>('idle')
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [queuePosition, setQueuePosition] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [isAiHandled, setIsAiHandled] = useState(true)
  const [showLeaveMessage, setShowLeaveMessage] = useState(false)
  const [leaveMessageText, setLeaveMessageText] = useState('')
  const [leaveMessageCategory, setLeaveMessageCategory] = useState<'sales' | 'billing' | 'technical'>('technical')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isMountedRef = useRef<boolean>(true)

  // Cleanup function to clear polling interval
  const clearPolling = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  // Track component mount state
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      // Ensure cleanup on all unmount paths
      clearPolling()
    }
  }, [clearPolling])

  // Poll for messages and status updates
  useEffect(() => {
    // Early return if no session or chat ended - also cleanup any existing interval
    if (!sessionId || chatStatus === 'ended') {
      clearPolling()
      return
    }

    // Define poll function inside effect to capture current sessionId
    const pollMessages = async () => {
      // Check mounted state before and after async operation
      if (!isMountedRef.current) return

      try {
        const data = await supportApi.getChatMessages(sessionId)

        // Double-check mount state after async call
        if (!isMountedRef.current) return

        setMessages(data.messages)

        if (data.status === 'active' && chatStatus === 'waiting') {
          setChatStatus('active')
          setQueuePosition(null)
        } else if (data.status === 'ended') {
          setChatStatus('ended')
          // Clear polling when chat ends
          clearPolling()
        } else if (data.status === 'waiting') {
          setQueuePosition(data.queue_position || null)
        }

        // Track if AI is handling or transferred to human
        if (data.is_ai_handled !== undefined) {
          setIsAiHandled(data.is_ai_handled)
        }
      } catch (err) {
        // Only log error if component is still mounted
        if (isMountedRef.current) {
          console.error('Failed to poll messages:', err)
        }
      }
    }

    // Clear any existing interval before starting new one (prevents race condition)
    clearPolling()

    // Initial poll immediately
    pollMessages()

    // Set up polling interval only if still mounted after initial call
    // Use a microtask to ensure this runs after pollMessages completes
    const timeoutId = setTimeout(() => {
      if (isMountedRef.current && chatStatus !== 'ended') {
        pollIntervalRef.current = setInterval(pollMessages, 3000)
      }
    }, 0)

    // Cleanup function
    return () => {
      clearTimeout(timeoutId)
      clearPolling()
    }
  }, [sessionId, chatStatus, clearPolling])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleStartChat = async () => {
    setError('')
    try {
      const session = await supportApi.startChat()
      setSessionId(session.id)
      setChatStatus(session.status === 'active' ? 'active' : 'waiting')
      setQueuePosition(session.queue_position || null)
      setIsAiHandled(session.is_ai_handled !== false)
    } catch (err: any) {
      setError(err.message || 'Failed to start chat')
    }
  }

  const handleLeaveQueue = () => {
    setShowLeaveMessage(true)
  }

  const handleSubmitLeaveMessage = async () => {
    if (!sessionId || !leaveMessageText.trim()) return
    setError('')

    try {
      await supportApi.leaveMessage(sessionId, leaveMessageText, leaveMessageCategory)
      await supportApi.endChat(sessionId)
      setChatStatus('ended')
      setShowLeaveMessage(false)
      setLeaveMessageText('')
    } catch (err: any) {
      // If leave message endpoint doesn't exist, just end chat
      await supportApi.endChat(sessionId)
      setChatStatus('ended')
      setShowLeaveMessage(false)
    }
  }

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !sessionId) return
    setIsSending(true)
    setError('')

    try {
      await supportApi.sendChatMessage(sessionId, newMessage.trim())
      setNewMessage('')
      // Immediately fetch new messages
      const data = await supportApi.getChatMessages(sessionId)
      setMessages(data.messages)
    } catch (err: any) {
      setError(err.message || 'Failed to send message')
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleEndChat = async () => {
    if (!sessionId) return
    try {
      await supportApi.endChat(sessionId)
      setChatStatus('ended')
    } catch (err) {
      console.error('Failed to end chat:', err)
    }
  }

  const handleNewChat = () => {
    setSessionId(null)
    setChatStatus('idle')
    setMessages([])
    setQueuePosition(null)
    setError('')
    setIsAiHandled(true)
  }

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 w-14 h-14 sm:w-16 sm:h-16 bg-gradient-to-r from-gold-600 to-gold-500 rounded-full shadow-lg hover:shadow-gold transition-all flex items-center justify-center z-50 touch-manipulation active:scale-95"
        aria-label="Open chat"
      >
        <MessageSquare className="h-6 w-6 sm:h-7 sm:w-7 text-premium-bg" />
      </button>
    )
  }

  return (
    <div
      className={`fixed inset-0 sm:inset-auto sm:bottom-6 sm:right-6 w-full sm:w-96 sm:max-w-[calc(100vw-2rem)] bg-premium-card border-0 sm:border border-premium-border sm:rounded-2xl shadow-2xl z-50 overflow-hidden transition-all ${
        isMinimized ? 'h-14 bottom-0 top-auto inset-x-0' : 'h-full sm:h-[min(600px,80vh)]'
      }`}
    >
      {/* Header */}
      <div className="h-14 sm:h-16 px-4 bg-gradient-to-r from-gold-600 to-gold-500 flex items-center justify-between safe-area-top">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 sm:w-11 sm:h-11 bg-white/20 rounded-full flex items-center justify-center">
            {isAiHandled ? (
              <Bot className="h-5 w-5 sm:h-6 sm:w-6 text-premium-bg" />
            ) : (
              <UserCircle className="h-5 w-5 sm:h-6 sm:w-6 text-premium-bg" />
            )}
          </div>
          <div>
            <p className="font-medium text-premium-bg text-base sm:text-lg">
              {isAiHandled ? 'Novah AI' : 'Support Chat'}
            </p>
            {chatStatus === 'active' && (
              <p className="text-xs sm:text-sm text-premium-bg/80">
                {isAiHandled ? 'AI Assistant' : 'Connected to Agent'}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-3 text-premium-bg/80 hover:text-premium-bg transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label={isMinimized ? 'Expand chat' : 'Minimize chat'}
          >
            <Minimize2 className="h-5 w-5" />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-3 text-premium-bg/80 hover:text-premium-bg transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Close chat"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Chat Content */}
          <div className="h-[calc(100%-3.5rem)] sm:h-[calc(100%-4rem)] flex flex-col">
            {chatStatus === 'idle' && (
              <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 text-center">
                <div className="w-20 h-20 sm:w-24 sm:h-24 bg-gold-500/20 rounded-full flex items-center justify-center mb-4 sm:mb-6">
                  <Bot className="h-10 w-10 sm:h-12 sm:w-12 text-gold-400" />
                </div>
                <h3 className="text-xl sm:text-2xl font-semibold text-white mb-2 sm:mb-3">Chat with Novah</h3>
                <p className="text-gray-400 text-sm sm:text-base mb-6 sm:mb-8 max-w-xs">
                  Our AI assistant will help you instantly. Need a human? Just ask!
                </p>
                {error && (
                  <div className="mb-4 text-sm text-red-400 flex items-center px-4 py-2 bg-red-500/10 rounded-lg">
                    <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
                    {error}
                  </div>
                )}
                <button
                  onClick={handleStartChat}
                  className="px-8 py-3 sm:py-4 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all text-base sm:text-lg min-h-[48px] touch-manipulation active:scale-98"
                >
                  Start Chat
                </button>
              </div>
            )}

            {chatStatus === 'waiting' && !showLeaveMessage && (
              <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 text-center">
                <div className="w-20 h-20 sm:w-24 sm:h-24 bg-blue-500/20 rounded-full flex items-center justify-center mb-4 sm:mb-6">
                  <Clock className="h-10 w-10 sm:h-12 sm:w-12 text-blue-400 animate-pulse" />
                </div>
                <h3 className="text-xl sm:text-2xl font-semibold text-white mb-2 sm:mb-3">Waiting for Agent</h3>
                <p className="text-gray-400 text-sm sm:text-base mb-2">
                  You're in the queue. An agent will be with you shortly.
                </p>
                {queuePosition && (
                  <p className="text-yellow-400 text-sm sm:text-base font-medium mb-4">
                    Queue position: #{queuePosition}
                  </p>
                )}
                <div className="flex flex-col gap-3 mt-4 w-full max-w-xs">
                  <button
                    onClick={handleLeaveQueue}
                    className="px-6 py-3 border border-premium-border text-gray-300 rounded-lg hover:bg-premium-surface transition-colors text-sm min-h-[48px] touch-manipulation"
                  >
                    Leave a Message Instead
                  </button>
                  <button
                    onClick={handleEndChat}
                    className="text-sm text-red-400 hover:text-red-300 min-h-[44px] touch-manipulation"
                  >
                    Leave Queue
                  </button>
                </div>
              </div>
            )}

            {chatStatus === 'waiting' && showLeaveMessage && (
              <div className="flex-1 flex flex-col p-4 sm:p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Leave a Message</h3>
                <p className="text-gray-400 text-sm mb-4">We'll get back to you via email.</p>

                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-2">Category</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['sales', 'billing', 'technical'] as const).map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setLeaveMessageCategory(cat)}
                        className={`py-2 px-3 rounded-lg text-sm capitalize transition-colors ${
                          leaveMessageCategory === cat
                            ? 'bg-gold-500/20 text-gold-400 border border-gold-500/50'
                            : 'bg-premium-surface text-gray-400 border border-premium-border hover:bg-premium-surface/80'
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex-1">
                  <label className="block text-sm text-gray-400 mb-2">Your Message</label>
                  <textarea
                    value={leaveMessageText}
                    onChange={(e) => setLeaveMessageText(e.target.value)}
                    placeholder="Describe your issue..."
                    className="w-full h-32 px-4 py-3 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500 resize-none"
                  />
                </div>

                <div className="flex gap-3 mt-4">
                  <button
                    onClick={() => setShowLeaveMessage(false)}
                    className="flex-1 py-3 border border-premium-border text-gray-300 rounded-lg hover:bg-premium-surface transition-colors text-sm min-h-[48px]"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleSubmitLeaveMessage}
                    disabled={!leaveMessageText.trim()}
                    className="flex-1 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50 text-sm min-h-[48px]"
                  >
                    Submit & Exit
                  </button>
                </div>
              </div>
            )}

            {(chatStatus === 'active' || chatStatus === 'ended') && (
              <>
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 overscroll-contain" aria-live="polite" aria-atomic="false">
                  {messages.length === 0 && chatStatus === 'active' && (
                    <div className="text-center text-gray-500 py-6 sm:py-8">
                      <p className="text-sm sm:text-base">Connected! Start the conversation.</p>
                    </div>
                  )}
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.sender_type === 'customer' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] sm:max-w-[80%] rounded-xl sm:rounded-lg p-3 sm:p-4 ${
                          msg.sender_type === 'customer'
                            ? 'bg-gold-500/20 text-white'
                            : 'bg-premium-surface text-white'
                        }`}
                      >
                        {msg.sender_type === 'bot' && (
                          <p className="text-xs text-purple-400 mb-1.5 flex items-center">
                            <Bot className="h-3 w-3 mr-1" />
                            Novah (AI)
                          </p>
                        )}
                        {msg.sender_type === 'agent' && (
                          <p className="text-xs text-blue-400 mb-1.5 flex items-center">
                            <Shield className="h-3 w-3 mr-1" />
                            {msg.sender_name || 'Support Agent'}
                          </p>
                        )}
                        <p className="text-sm sm:text-base whitespace-pre-wrap leading-relaxed">{msg.message}</p>
                        <p className="text-xs text-gray-500 mt-1.5 text-right">
                          {formatTime(msg.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input or Ended State */}
                {chatStatus === 'active' ? (
                  <div className="p-3 sm:p-4 border-t border-premium-border safe-area-bottom bg-premium-card">
                    {error && (
                      <div className="mb-2 text-xs text-red-400 px-2 py-1 bg-red-500/10 rounded">{error}</div>
                    )}
                    <div className="flex space-x-2 sm:space-x-3">
                      <input
                        type="text"
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type a message..."
                        className="flex-1 px-4 py-3 bg-premium-surface border border-premium-border rounded-xl sm:rounded-lg text-white text-base sm:text-sm focus:outline-none focus:border-gold-500 min-h-[48px]"
                      />
                      <button
                        onClick={handleSendMessage}
                        disabled={!newMessage.trim() || isSending}
                        className="px-4 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg rounded-xl sm:rounded-lg hover:shadow-gold transition-all disabled:opacity-50 min-w-[48px] min-h-[48px] flex items-center justify-center touch-manipulation active:scale-95"
                        aria-label="Send message"
                      >
                        <Send className="h-5 w-5" />
                      </button>
                    </div>
                    <div className="flex justify-between items-center mt-3 px-1">
                      <p className="text-xs text-gray-500 hidden sm:block">Press Enter to send</p>
                      <button
                        onClick={handleEndChat}
                        className="text-sm sm:text-xs text-red-400 hover:text-red-300 min-h-[44px] touch-manipulation px-2"
                      >
                        End Chat
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 sm:p-6 border-t border-premium-border text-center safe-area-bottom">
                    <p className="text-gray-400 text-base sm:text-sm mb-4 sm:mb-3">Chat ended</p>
                    <button
                      onClick={handleNewChat}
                      className="px-6 py-3 bg-premium-surface text-white text-base sm:text-sm rounded-xl sm:rounded-lg hover:bg-premium-surface/80 transition-colors min-h-[48px] touch-manipulation"
                    >
                      Start New Chat
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

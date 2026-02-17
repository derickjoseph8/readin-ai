'use client'

import { useState, useEffect, useRef } from 'react'
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
  const [isRequestingHuman, setIsRequestingHuman] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Poll for messages and status updates
  useEffect(() => {
    if (sessionId && chatStatus !== 'ended') {
      const pollMessages = async () => {
        try {
          const data = await supportApi.getChatMessages(sessionId)
          setMessages(data.messages)

          if (data.status === 'active' && chatStatus === 'waiting') {
            setChatStatus('active')
            setQueuePosition(null)
          } else if (data.status === 'ended') {
            setChatStatus('ended')
          } else if (data.status === 'waiting') {
            setQueuePosition(data.queue_position || null)
          }

          // Track if AI is handling or transferred to human
          if (data.is_ai_handled !== undefined) {
            setIsAiHandled(data.is_ai_handled)
          }
        } catch (err) {
          console.error('Failed to poll messages:', err)
        }
      }

      pollMessages()
      pollIntervalRef.current = setInterval(pollMessages, 3000)

      return () => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
      }
    }
  }, [sessionId, chatStatus])

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

  const handleRequestHuman = async () => {
    if (!sessionId) return
    setIsRequestingHuman(true)
    setError('')

    try {
      await supportApi.requestHumanAgent(sessionId)
      setIsAiHandled(false)
      setChatStatus('waiting')
    } catch (err: any) {
      setError(err.message || 'Failed to request human agent')
    } finally {
      setIsRequestingHuman(false)
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
        className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 w-12 h-12 sm:w-14 sm:h-14 bg-gradient-to-r from-gold-600 to-gold-500 rounded-full shadow-lg hover:shadow-gold transition-all flex items-center justify-center z-50"
        aria-label="Open chat"
      >
        <MessageSquare className="h-5 w-5 sm:h-6 sm:w-6 text-premium-bg" />
      </button>
    )
  }

  return (
    <div
      className={`fixed bottom-0 right-0 sm:bottom-6 sm:right-6 w-full sm:w-96 sm:max-w-[calc(100vw-2rem)] bg-premium-card border border-premium-border sm:rounded-2xl shadow-2xl z-50 overflow-hidden transition-all ${
        isMinimized ? 'h-14' : 'h-[100dvh] sm:h-[500px]'
      }`}
    >
      {/* Header */}
      <div className="h-14 px-4 bg-gradient-to-r from-gold-600 to-gold-500 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
            {isAiHandled ? (
              <Bot className="h-4 w-4 text-premium-bg" />
            ) : (
              <UserCircle className="h-4 w-4 text-premium-bg" />
            )}
          </div>
          <div>
            <p className="font-medium text-premium-bg">
              {isAiHandled ? 'Novah AI' : 'Support Chat'}
            </p>
            {chatStatus === 'active' && (
              <p className="text-xs text-premium-bg/80">
                {isAiHandled ? 'AI Assistant' : 'Connected to Agent'}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-2 text-premium-bg/80 hover:text-premium-bg transition-colors"
          >
            <Minimize2 className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 text-premium-bg/80 hover:text-premium-bg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Chat Content */}
          <div className="h-[calc(100%-3.5rem)] flex flex-col">
            {chatStatus === 'idle' && (
              <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-16 h-16 bg-gold-500/20 rounded-full flex items-center justify-center mb-4">
                  <Bot className="h-8 w-8 text-gold-400" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">Chat with Novah</h3>
                <p className="text-gray-400 text-sm mb-6">
                  Our AI assistant will help you instantly. Need a human? Just ask!
                </p>
                {error && (
                  <div className="mb-4 text-sm text-red-400 flex items-center">
                    <AlertCircle className="h-4 w-4 mr-2" />
                    {error}
                  </div>
                )}
                <button
                  onClick={handleStartChat}
                  className="px-6 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all"
                >
                  Start Chat
                </button>
              </div>
            )}

            {chatStatus === 'waiting' && (
              <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mb-4">
                  <Clock className="h-8 w-8 text-blue-400 animate-pulse" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">Waiting for Agent</h3>
                <p className="text-gray-400 text-sm mb-2">
                  You're in the queue. An agent will be with you shortly.
                </p>
                {queuePosition && (
                  <p className="text-yellow-400 text-sm">
                    Queue position: #{queuePosition}
                  </p>
                )}
              </div>
            )}

            {(chatStatus === 'active' || chatStatus === 'ended') && (
              <>
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.length === 0 && chatStatus === 'active' && (
                    <div className="text-center text-gray-500 py-4">
                      <p>Connected! Start the conversation.</p>
                    </div>
                  )}
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.sender_type === 'customer' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg p-3 ${
                          msg.sender_type === 'customer'
                            ? 'bg-gold-500/20 text-white'
                            : 'bg-premium-surface text-white'
                        }`}
                      >
                        {msg.sender_type === 'bot' && (
                          <p className="text-xs text-purple-400 mb-1 flex items-center">
                            <Bot className="h-3 w-3 mr-1" />
                            Novah (AI)
                          </p>
                        )}
                        {msg.sender_type === 'agent' && (
                          <p className="text-xs text-blue-400 mb-1 flex items-center">
                            <Shield className="h-3 w-3 mr-1" />
                            {msg.sender_name || 'Support Agent'}
                          </p>
                        )}
                        <p className="text-sm whitespace-pre-wrap">{msg.message}</p>
                        <p className="text-xs text-gray-500 mt-1 text-right">
                          {formatTime(msg.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input or Ended State */}
                {chatStatus === 'active' ? (
                  <div className="p-3 border-t border-premium-border">
                    {error && (
                      <div className="mb-2 text-xs text-red-400">{error}</div>
                    )}
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type a message..."
                        className="flex-1 px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                      />
                      <button
                        onClick={handleSendMessage}
                        disabled={!newMessage.trim() || isSending}
                        className="px-3 py-2 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
                      >
                        <Send className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="flex justify-between items-center mt-2">
                      <p className="text-xs text-gray-500">Press Enter to send</p>
                      <div className="flex items-center gap-3">
                        {isAiHandled && (
                          <button
                            onClick={handleRequestHuman}
                            disabled={isRequestingHuman}
                            className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50"
                          >
                            {isRequestingHuman ? 'Connecting...' : 'Talk to Human'}
                          </button>
                        )}
                        <button
                          onClick={handleEndChat}
                          className="text-xs text-red-400 hover:text-red-300"
                        >
                          End Chat
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 border-t border-premium-border text-center">
                    <p className="text-gray-400 text-sm mb-3">Chat ended</p>
                    <button
                      onClick={handleNewChat}
                      className="px-4 py-2 bg-premium-surface text-white text-sm rounded-lg hover:bg-premium-surface/80 transition-colors"
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

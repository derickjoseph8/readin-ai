'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
  MessageSquare,
  User,
  Clock,
  Send,
  X,
  Ticket
} from 'lucide-react'
import { useChatQueue, useAgentStatus } from '@/lib/hooks/useAdmin'
import { usePermissions } from '@/lib/hooks/usePermissions'
import { adminApi, ChatSession, ChatMessage } from '@/lib/api/admin'

function QueueCard({
  session,
  onAccept,
  isAccepting
}: {
  session: ChatSession
  onAccept: () => void
  isAccepting: boolean
}) {
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    return `${diffMins}m ago`
  }

  return (
    <div className="bg-premium-surface rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center">
            <User className="h-5 w-5 text-blue-400" />
          </div>
          <div>
            <p className="font-medium text-white">{session.user_name || 'Customer'}</p>
            <p className="text-sm text-gray-500">
              {session.team_name || 'General Support'}
            </p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs text-gray-500 flex items-center">
            <Clock className="h-3 w-3 mr-1" />
            {formatTime(session.started_at)}
          </span>
          {session.queue_position && (
            <span className="text-xs text-yellow-400">
              Queue #{session.queue_position}
            </span>
          )}
        </div>
      </div>
      <button
        onClick={onAccept}
        disabled={isAccepting}
        className="w-full py-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
      >
        {isAccepting ? 'Accepting...' : 'Accept Chat'}
      </button>
    </div>
  )
}

function ActiveChatCard({
  session,
  onSelect,
  isSelected
}: {
  session: ChatSession
  onSelect: () => void
  isSelected: boolean
}) {
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-4 rounded-lg transition-colors ${
        isSelected ? 'bg-gold-500/20 border border-gold-500/30' : 'bg-premium-surface hover:bg-premium-surface/80'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center">
            <User className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <p className="font-medium text-white">{session.user_name || 'Customer'}</p>
            <p className="text-sm text-gray-500">{session.team_name || 'General'}</p>
          </div>
        </div>
        <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
      </div>
    </button>
  )
}

function ChatWindow({
  session,
  onClose,
  onEndChat
}: {
  session: ChatSession
  onClose: () => void
  onEndChat: () => void
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const [showEndMenu, setShowEndMenu] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const fetchMessages = async () => {
    try {
      const data = await adminApi.getChatMessages(session.id)
      setMessages(data)
    } catch (error) {
      console.error('Failed to fetch messages:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchMessages()
    const interval = setInterval(fetchMessages, 3000)
    return () => clearInterval(interval)
  }, [session.id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!newMessage.trim()) return
    setIsSending(true)

    try {
      await adminApi.sendChatMessage(session.id, newMessage)
      setNewMessage('')
      fetchMessages()
    } catch (error) {
      console.error('Failed to send message:', error)
    } finally {
      setIsSending(false)
    }
  }

  const handleEndChat = async (createTicket: boolean = false) => {
    try {
      await adminApi.endChat(session.id, createTicket, createTicket ? 'Chat conversation' : undefined)
      onEndChat()
    } catch (error) {
      console.error('Failed to end chat:', error)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-premium-border flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center">
            <User className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <p className="font-medium text-white">{session.user_name || 'Customer'}</p>
            <p className="text-sm text-gray-500">
              {session.team_name || 'General Support'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <div className="relative">
            <button
              onClick={() => setShowEndMenu(!showEndMenu)}
              className="px-3 py-1.5 text-sm bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
            >
              End Chat
            </button>
            {showEndMenu && (
              <div className="absolute right-0 top-full mt-1 bg-premium-card border border-premium-border rounded-lg shadow-lg z-10 min-w-[180px]">
                <button
                  onClick={() => handleEndChat(false)}
                  className="w-full text-left px-4 py-2 text-sm text-white hover:bg-premium-surface rounded-t-lg"
                >
                  End Chat
                </button>
                <button
                  onClick={() => handleEndChat(true)}
                  className="w-full text-left px-4 py-2 text-sm text-white hover:bg-premium-surface rounded-b-lg flex items-center"
                >
                  <Ticket className="h-4 w-4 mr-2" />
                  End & Create Ticket
                </button>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-white transition-colors lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-gold-400"></div>
          </div>
        ) : messages.length > 0 ? (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.sender_type === 'agent' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-lg p-3 ${
                  msg.sender_type === 'agent'
                    ? 'bg-gold-500/20 text-white'
                    : 'bg-premium-surface text-white'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.message}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(msg.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center text-gray-500 py-8">
            No messages yet. Start the conversation!
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-premium-border">
        <div className="flex space-x-2">
          <textarea
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message..."
            className="flex-1 px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500 resize-none"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!newMessage.trim() || isSending}
            className="px-4 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ChatPage() {
  const router = useRouter()
  const { permissions } = usePermissions()
  const { sessions, waiting, active, refresh } = useChatQueue()
  const { status: agentStatus, updateStatus } = useAgentStatus()
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null)
  const [acceptingId, setAcceptingId] = useState<number | null>(null)

  // Permission check - redirect if not allowed
  if (!permissions.canViewChatQueue) {
    if (typeof window !== 'undefined') {
      router.push('/dashboard')
    }
    return null
  }

  const waitingSessions = sessions.filter((s) => s.status === 'waiting')
  const activeSessions = sessions.filter((s) => s.status === 'active' && s.agent_id)

  const handleAccept = async (sessionId: number) => {
    setAcceptingId(sessionId)
    try {
      const session = await adminApi.acceptChat(sessionId)
      setSelectedSession(session)
      refresh()
    } catch (error) {
      console.error('Failed to accept chat:', error)
    } finally {
      setAcceptingId(null)
    }
  }

  const handleEndChat = () => {
    setSelectedSession(null)
    refresh()
  }

  const isOnline = agentStatus?.status === 'online'

  return (
    <div className="h-[calc(100vh-6rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Chat</h1>
          <p className="text-gray-400 mt-1">
            {waiting} waiting, {active} active
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => updateStatus(isOnline ? 'offline' : 'online')}
            className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
              isOnline
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-gray-500/20 text-gray-400'
            }`}
          >
            <div className={`w-2 h-2 rounded-full mr-2 ${isOnline ? 'bg-emerald-400' : 'bg-gray-400'}`} />
            {isOnline ? 'Online' : 'Offline'}
          </button>
        </div>
      </div>

      {!isOnline && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-6 flex items-center">
          <MessageSquare className="h-5 w-5 text-yellow-400 mr-3" />
          <p className="text-yellow-400">You are offline. Go online to receive chats.</p>
        </div>
      )}

      <div className="flex h-[calc(100%-6rem)] gap-6">
        {/* Sidebar */}
        <div className="w-80 flex flex-col space-y-6">
          {/* Queue */}
          <div className="bg-premium-card border border-premium-border rounded-xl p-4 flex-1 overflow-hidden flex flex-col">
            <h2 className="font-semibold text-white mb-4 flex items-center">
              <Clock className="h-4 w-4 mr-2 text-yellow-400" />
              Waiting ({waitingSessions.length})
            </h2>
            <div className="flex-1 overflow-y-auto space-y-3">
              {waitingSessions.length > 0 ? (
                waitingSessions.map((session) => (
                  <QueueCard
                    key={session.id}
                    session={session}
                    onAccept={() => handleAccept(session.id)}
                    isAccepting={acceptingId === session.id}
                  />
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <Clock className="h-8 w-8 mx-auto mb-2 text-gray-600" />
                  <p>No chats waiting</p>
                </div>
              )}
            </div>
          </div>

          {/* Active Chats */}
          <div className="bg-premium-card border border-premium-border rounded-xl p-4 flex-1 overflow-hidden flex flex-col">
            <h2 className="font-semibold text-white mb-4 flex items-center">
              <MessageSquare className="h-4 w-4 mr-2 text-emerald-400" />
              Active ({activeSessions.length})
            </h2>
            <div className="flex-1 overflow-y-auto space-y-3">
              {activeSessions.length > 0 ? (
                activeSessions.map((session) => (
                  <ActiveChatCard
                    key={session.id}
                    session={session}
                    onSelect={() => setSelectedSession(session)}
                    isSelected={selectedSession?.id === session.id}
                  />
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <MessageSquare className="h-8 w-8 mx-auto mb-2 text-gray-600" />
                  <p>No active chats</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Chat Window */}
        <div className={`flex-1 bg-premium-card border border-premium-border rounded-xl overflow-hidden ${selectedSession ? '' : 'hidden lg:flex'}`}>
          {selectedSession ? (
            <ChatWindow
              session={selectedSession}
              onClose={() => setSelectedSession(null)}
              onEndChat={handleEndChat}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 text-gray-600" />
                <p>Select a chat to start messaging</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

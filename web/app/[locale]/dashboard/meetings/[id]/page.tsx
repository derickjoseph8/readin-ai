'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, Calendar, Clock, MessageSquare, User, Copy, Check } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/hooks/useAuth';

interface Conversation {
  id: number;
  question: string;
  response: string;
  speaker: string | null;
  created_at: string;
}

interface MeetingDetail {
  id: number;
  title: string | null;
  meeting_type: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  summary: string | null;
  conversations: Conversation[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://18.198.173.81:7500';

export default function MeetingDetailPage({ params }: { params: { id: string } }) {
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const { token } = useAuth();
  const t = useTranslations('meetings');
  const tc = useTranslations('common');

  useEffect(() => {
    const fetchMeeting = async () => {
      if (!token) return;

      try {
        const response = await fetch(`${API_URL}/meetings/${params.id}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setMeeting(data);
        }
      } catch (error) {
        console.error('Failed to fetch meeting:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMeeting();
  }, [params.id, token]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '—';
    const mins = Math.floor(seconds / 60);
    const hrs = Math.floor(mins / 60);
    if (hrs > 0) return `${hrs}h ${mins % 60}m`;
    return `${mins}m`;
  };

  const copyToClipboard = async (text: string, id: number) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">Meeting not found</p>
        <Link href="/dashboard/meetings" className="text-gold-400 hover:text-gold-300 mt-2 inline-block">
          Back to meetings
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/dashboard/meetings"
        className="inline-flex items-center text-gray-400 hover:text-gold-400 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        {tc('back')} to {t('title')}
      </Link>

      {/* Meeting Header */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h1 className="text-2xl font-bold text-white">
          {meeting.title || `${meeting.meeting_type} Meeting`}
        </h1>

        <div className="flex flex-wrap gap-6 mt-4">
          <div className="flex items-center text-gray-400">
            <Calendar className="h-5 w-5 mr-2 text-gold-400" />
            {formatDate(meeting.started_at)}
          </div>
          <div className="flex items-center text-gray-400">
            <Clock className="h-5 w-5 mr-2 text-gold-400" />
            {formatTime(meeting.started_at)} - {meeting.ended_at ? formatTime(meeting.ended_at) : 'Ongoing'}
          </div>
          <div className="flex items-center text-gray-400">
            <MessageSquare className="h-5 w-5 mr-2 text-gold-400" />
            {meeting.conversations.length} responses
          </div>
          <div className="flex items-center text-gray-400">
            <Clock className="h-5 w-5 mr-2 text-emerald-400" />
            {t('duration')}: {formatDuration(meeting.duration_seconds)}
          </div>
        </div>

        {meeting.summary && (
          <div className="mt-6 p-4 bg-premium-surface rounded-lg border border-premium-border">
            <h3 className="text-sm font-medium text-gold-400 mb-2">{t('summary')}</h3>
            <p className="text-gray-300">{meeting.summary}</p>
          </div>
        )}
      </div>

      {/* Conversations */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white">Conversation History</h2>

        {meeting.conversations.length > 0 ? (
          meeting.conversations.map((conv) => (
            <div
              key={conv.id}
              className="bg-premium-card border border-premium-border rounded-xl p-5"
            >
              {/* Question */}
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 bg-blue-500/20 rounded-full flex items-center justify-center">
                    <User className="h-3 w-3 text-blue-400" />
                  </div>
                  <span className="text-sm text-gray-400">
                    {conv.speaker || 'Speaker'}
                  </span>
                  <span className="text-xs text-gray-600">
                    {new Date(conv.created_at).toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
                <p className="text-gray-300 pl-8">{conv.question}</p>
              </div>

              {/* Response */}
              <div className="pl-8 pt-4 border-t border-premium-border">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-gold-500/20 rounded-full flex items-center justify-center">
                      <span className="text-xs font-bold text-gold-400">R</span>
                    </div>
                    <span className="text-sm text-gold-400">ReadIn AI</span>
                  </div>
                  <button
                    onClick={() => copyToClipboard(conv.response, conv.id)}
                    className="p-1.5 text-gray-500 hover:text-gold-400 transition-colors"
                    title="Copy response"
                  >
                    {copiedId === conv.id ? (
                      <Check className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <div className="text-emerald-400 whitespace-pre-wrap">{conv.response}</div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12 bg-premium-card border border-premium-border rounded-xl">
            <MessageSquare className="h-12 w-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No conversations recorded</p>
          </div>
        )}
      </div>
    </div>
  );
}

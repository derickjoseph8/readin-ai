'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Search, Filter, Calendar, Clock, MessageSquare, ChevronRight } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useMeetings } from '@/lib/hooks/useMeetings';

export default function MeetingsPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const { meetings, isLoading, totalPages } = useMeetings(page, 10);
  const t = useTranslations('meetings');
  const tc = useTranslations('common');

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
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

  const filteredMeetings = meetings.filter(meeting =>
    (meeting.title || '').toLowerCase().includes(search.toLowerCase()) ||
    meeting.meeting_type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">{t('title')}</h1>
        <p className="text-gray-400 mt-1">{t('subtitle')}</p>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
          <input
            type="text"
            placeholder={t('search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg focus:border-gold-500 focus:outline-none text-white"
          />
        </div>
        <button className="flex items-center px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white hover:border-gold-500/30 transition-colors">
          <Filter className="h-5 w-5 mr-2" />
          {t('filter')}
        </button>
      </div>

      {/* Meetings List */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400 mx-auto"></div>
          <p className="mt-4 text-gray-400">{tc('loading')}</p>
        </div>
      ) : filteredMeetings.length > 0 ? (
        <div className="space-y-3">
          {filteredMeetings.map((meeting) => (
            <Link
              key={meeting.id}
              href={`/dashboard/meetings/${meeting.id}`}
              className="block bg-premium-card border border-premium-border rounded-xl p-4 hover:border-gold-500/30 transition-colors group"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gold-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Calendar className="h-5 w-5 text-gold-400" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-medium text-white truncate group-hover:text-gold-400 transition-colors">
                        {meeting.title || `${meeting.meeting_type} Meeting`}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {formatDate(meeting.started_at)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-6 ml-4">
                  <div className="text-right hidden sm:block">
                    <div className="flex items-center text-gray-400 text-sm">
                      <Clock className="h-4 w-4 mr-1" />
                      {formatDuration(meeting.duration_seconds)}
                    </div>
                  </div>
                  <div className="text-right hidden sm:block">
                    <div className="flex items-center text-gray-400 text-sm">
                      <MessageSquare className="h-4 w-4 mr-1" />
                      {meeting.conversation_count}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-600 group-hover:text-gold-400 transition-colors" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-premium-card border border-premium-border rounded-xl">
          <Calendar className="h-12 w-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">{t('noMeetings')}</p>
          <p className="text-gray-500 text-sm mt-1">
            Start a meeting with ReadIn AI to see your history here
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {tc('previous')}
          </button>
          <span className="text-gray-400 px-4">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {tc('next')}
          </button>
        </div>
      )}
    </div>
  );
}

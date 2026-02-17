'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import {
  MessageSquare,
  Video,
  Check,
  X,
  ExternalLink,
  Settings,
  Bell,
  RefreshCw,
  Send,
  ChevronDown,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import {
  getIntegrationsStatus,
  getSlackAuthUrl,
  getSlackChannels,
  disconnectSlack,
  getTeamsAuthUrl,
  getTeamsList,
  getTeamsChannels,
  disconnectTeams,
  updateIntegrationSettings,
  sendTestNotification,
  IntegrationStatus,
  Channel,
  Team
} from '@/lib/api/integrations'

export default function IntegrationsPage() {
  const searchParams = useSearchParams()
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Slack state
  const [slackChannels, setSlackChannels] = useState<Channel[]>([])
  const [slackChannelsLoading, setSlackChannelsLoading] = useState(false)
  const [slackSelectedChannel, setSlackSelectedChannel] = useState<string>('')
  const [slackSettingsOpen, setSlackSettingsOpen] = useState(false)

  // Teams state
  const [teamsList, setTeamsList] = useState<Team[]>([])
  const [teamsChannels, setTeamsChannels] = useState<Channel[]>([])
  const [teamsLoading, setTeamsLoading] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState<string>('')
  const [teamsSelectedChannel, setTeamsSelectedChannel] = useState<string>('')
  const [teamsSettingsOpen, setTeamsSettingsOpen] = useState(false)

  // Settings state
  const [settings, setSettings] = useState<{
    slack: {
      notifications_enabled: boolean
      meeting_summaries_enabled: boolean
      action_item_reminders_enabled: boolean
      briefing_notifications_enabled: boolean
    }
    teams: {
      notifications_enabled: boolean
      meeting_summaries_enabled: boolean
      action_item_reminders_enabled: boolean
      briefing_notifications_enabled: boolean
    }
  }>({
    slack: {
      notifications_enabled: true,
      meeting_summaries_enabled: true,
      action_item_reminders_enabled: true,
      briefing_notifications_enabled: true,
    },
    teams: {
      notifications_enabled: true,
      meeting_summaries_enabled: true,
      action_item_reminders_enabled: true,
      briefing_notifications_enabled: true,
    }
  })

  // Check for success/error from OAuth callback
  useEffect(() => {
    const successParam = searchParams.get('success')
    const errorParam = searchParams.get('error')

    if (successParam === 'slack_connected') {
      setSuccess('Slack connected successfully!')
      // Clear the URL params
      window.history.replaceState({}, '', '/dashboard/settings/integrations')
    } else if (successParam === 'teams_connected') {
      setSuccess('Microsoft Teams connected successfully!')
      window.history.replaceState({}, '', '/dashboard/settings/integrations')
    } else if (errorParam === 'slack_auth_failed') {
      setError('Failed to connect Slack. Please try again.')
      window.history.replaceState({}, '', '/dashboard/settings/integrations')
    } else if (errorParam === 'teams_auth_failed') {
      setError('Failed to connect Microsoft Teams. Please try again.')
      window.history.replaceState({}, '', '/dashboard/settings/integrations')
    }
  }, [searchParams])

  // Load integrations status
  useEffect(() => {
    loadIntegrations()
  }, [])

  async function loadIntegrations() {
    try {
      setLoading(true)
      const data = await getIntegrationsStatus()
      setIntegrations(data.integrations)

      // Update settings state from loaded data
      const slackInt = data.integrations.find(i => i.provider === 'slack')
      const teamsInt = data.integrations.find(i => i.provider === 'teams')

      if (slackInt) {
        setSettings(prev => ({
          ...prev,
          slack: {
            notifications_enabled: slackInt.notifications_enabled,
            meeting_summaries_enabled: slackInt.meeting_summaries_enabled,
            action_item_reminders_enabled: slackInt.action_item_reminders_enabled,
            briefing_notifications_enabled: true,
          }
        }))
      }

      if (teamsInt) {
        setSettings(prev => ({
          ...prev,
          teams: {
            notifications_enabled: teamsInt.notifications_enabled,
            meeting_summaries_enabled: teamsInt.meeting_summaries_enabled,
            action_item_reminders_enabled: teamsInt.action_item_reminders_enabled,
            briefing_notifications_enabled: true,
          }
        }))
      }
    } catch (err) {
      setError('Failed to load integrations')
    } finally {
      setLoading(false)
    }
  }

  // Slack functions
  async function handleConnectSlack() {
    try {
      const data = await getSlackAuthUrl()
      window.location.href = data.authorization_url
    } catch (err) {
      setError('Failed to initiate Slack connection')
    }
  }

  async function handleDisconnectSlack() {
    if (!confirm('Are you sure you want to disconnect Slack?')) return

    try {
      await disconnectSlack()
      setSuccess('Slack disconnected')
      loadIntegrations()
    } catch (err) {
      setError('Failed to disconnect Slack')
    }
  }

  async function loadSlackChannels() {
    try {
      setSlackChannelsLoading(true)
      const data = await getSlackChannels()
      setSlackChannels(data.channels)
    } catch (err) {
      setError('Failed to load Slack channels')
    } finally {
      setSlackChannelsLoading(false)
    }
  }

  async function handleSlackTestMessage() {
    if (!slackSelectedChannel) {
      setError('Please select a channel first')
      return
    }

    try {
      await sendTestNotification('slack', slackSelectedChannel)
      setSuccess('Test message sent to Slack!')
    } catch (err) {
      setError('Failed to send test message')
    }
  }

  async function handleSaveSlackSettings() {
    try {
      await updateIntegrationSettings('slack', {
        ...settings.slack,
        default_channel_id: slackSelectedChannel || undefined
      })
      setSuccess('Slack settings saved')
    } catch (err) {
      setError('Failed to save settings')
    }
  }

  // Teams functions
  async function handleConnectTeams() {
    try {
      const data = await getTeamsAuthUrl()
      window.location.href = data.authorization_url
    } catch (err) {
      setError('Failed to initiate Teams connection')
    }
  }

  async function handleDisconnectTeams() {
    if (!confirm('Are you sure you want to disconnect Microsoft Teams?')) return

    try {
      await disconnectTeams()
      setSuccess('Microsoft Teams disconnected')
      loadIntegrations()
    } catch (err) {
      setError('Failed to disconnect Teams')
    }
  }

  async function loadTeamsList() {
    try {
      setTeamsLoading(true)
      const data = await getTeamsList()
      setTeamsList(data.teams)
    } catch (err) {
      setError('Failed to load Teams')
    } finally {
      setTeamsLoading(false)
    }
  }

  async function loadTeamsChannels(teamId: string) {
    try {
      setTeamsLoading(true)
      const data = await getTeamsChannels(teamId)
      setTeamsChannels(data.channels)
    } catch (err) {
      setError('Failed to load channels')
    } finally {
      setTeamsLoading(false)
    }
  }

  async function handleTeamsTestMessage() {
    if (!selectedTeam || !teamsSelectedChannel) {
      setError('Please select a team and channel first')
      return
    }

    try {
      // Format: team_id:channel_id
      const channelId = `${selectedTeam}:${teamsSelectedChannel}`
      await sendTestNotification('teams', channelId)
      setSuccess('Test message sent to Teams!')
    } catch (err) {
      setError('Failed to send test message')
    }
  }

  async function handleSaveTeamsSettings() {
    try {
      const channelId = selectedTeam && teamsSelectedChannel
        ? `${selectedTeam}:${teamsSelectedChannel}`
        : undefined

      await updateIntegrationSettings('teams', {
        ...settings.teams,
        default_channel_id: channelId
      })
      setSuccess('Teams settings saved')
    } catch (err) {
      setError('Failed to save settings')
    }
  }

  const slackIntegration = integrations.find(i => i.provider === 'slack')
  const teamsIntegration = integrations.find(i => i.provider === 'teams')

  // Auto-clear messages
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [success])

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [error])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gold-400" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Integrations</h1>
        <p className="text-gray-400 mt-1">
          Connect ReadIn AI with your favorite collaboration tools to receive meeting summaries and reminders.
        </p>
      </div>

      {/* Status Messages */}
      {success && (
        <div className="flex items-center p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
          <CheckCircle className="h-5 w-5 text-emerald-400 mr-3" />
          <span className="text-emerald-400">{success}</span>
        </div>
      )}

      {error && (
        <div className="flex items-center p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <AlertCircle className="h-5 w-5 text-red-400 mr-3" />
          <span className="text-red-400">{error}</span>
        </div>
      )}

      {/* Slack Integration */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-[#4A154B] rounded-lg flex items-center justify-center">
              <MessageSquare className="h-6 w-6 text-white" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-white">Slack</h3>
              <p className="text-sm text-gray-400">
                {slackIntegration?.is_connected
                  ? `Connected to ${slackIntegration.workspace_name}`
                  : 'Receive notifications in Slack channels'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {slackIntegration?.is_connected ? (
              <>
                <span className="flex items-center text-sm text-emerald-400">
                  <Check className="h-4 w-4 mr-1" />
                  Connected
                </span>
                <button
                  onClick={handleDisconnectSlack}
                  className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 border border-red-500/30 rounded-lg hover:bg-red-500/10 transition-colors"
                >
                  Disconnect
                </button>
              </>
            ) : slackIntegration?.is_configured ? (
              <button
                onClick={handleConnectSlack}
                className="px-4 py-2 bg-[#4A154B] text-white rounded-lg hover:bg-[#5c1c5f] transition-colors flex items-center"
              >
                Connect Slack
                <ExternalLink className="h-4 w-4 ml-2" />
              </button>
            ) : (
              <span className="text-sm text-gray-500">Not configured</span>
            )}
          </div>
        </div>

        {/* Slack Settings (when connected) */}
        {slackIntegration?.is_connected && (
          <div className="mt-6 pt-6 border-t border-premium-border">
            <button
              onClick={() => {
                setSlackSettingsOpen(!slackSettingsOpen)
                if (!slackSettingsOpen && slackChannels.length === 0) {
                  loadSlackChannels()
                }
              }}
              className="flex items-center justify-between w-full text-left"
            >
              <span className="flex items-center text-white">
                <Settings className="h-4 w-4 mr-2" />
                Notification Settings
              </span>
              <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${slackSettingsOpen ? 'rotate-180' : ''}`} />
            </button>

            {slackSettingsOpen && (
              <div className="mt-4 space-y-4">
                {/* Channel Selection */}
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Default Channel</label>
                  <div className="flex space-x-2">
                    <select
                      value={slackSelectedChannel}
                      onChange={(e) => setSlackSelectedChannel(e.target.value)}
                      className="flex-1 bg-premium-surface border border-premium-border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-gold-500"
                    >
                      <option value="">Select a channel...</option>
                      {slackChannels.map((channel) => (
                        <option key={channel.id} value={channel.id}>
                          #{channel.name} {channel.is_private ? '(private)' : ''}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={loadSlackChannels}
                      disabled={slackChannelsLoading}
                      className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white transition-colors"
                    >
                      <RefreshCw className={`h-4 w-4 ${slackChannelsLoading ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                      onClick={handleSlackTestMessage}
                      disabled={!slackSelectedChannel}
                      className="px-4 py-2 bg-gold-500 text-premium-bg rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Test
                    </button>
                  </div>
                </div>

                {/* Notification Types */}
                <div className="space-y-3">
                  <label className="block text-sm text-gray-400">Notification Types</label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.slack.meeting_summaries_enabled}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        slack: { ...prev.slack, meeting_summaries_enabled: e.target.checked }
                      }))}
                      className="w-4 h-4 rounded border-gray-600 text-gold-500 focus:ring-gold-500 bg-premium-surface"
                    />
                    <span className="ml-3 text-white">Meeting Summaries</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.slack.action_item_reminders_enabled}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        slack: { ...prev.slack, action_item_reminders_enabled: e.target.checked }
                      }))}
                      className="w-4 h-4 rounded border-gray-600 text-gold-500 focus:ring-gold-500 bg-premium-surface"
                    />
                    <span className="ml-3 text-white">Action Item Reminders</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.slack.briefing_notifications_enabled}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        slack: { ...prev.slack, briefing_notifications_enabled: e.target.checked }
                      }))}
                      className="w-4 h-4 rounded border-gray-600 text-gold-500 focus:ring-gold-500 bg-premium-surface"
                    />
                    <span className="ml-3 text-white">Pre-Meeting Briefings</span>
                  </label>
                </div>

                <button
                  onClick={handleSaveSlackSettings}
                  className="px-4 py-2 bg-gold-500 text-premium-bg rounded-lg hover:bg-gold-400 transition-colors"
                >
                  Save Settings
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Microsoft Teams Integration */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center">
            <div className="w-12 h-12 bg-[#464EB8] rounded-lg flex items-center justify-center">
              <Video className="h-6 w-6 text-white" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-white">Microsoft Teams</h3>
              <p className="text-sm text-gray-400">
                {teamsIntegration?.is_connected
                  ? `Connected as ${teamsIntegration.user_name}`
                  : 'Post updates to Teams channels'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {teamsIntegration?.is_connected ? (
              <>
                <span className="flex items-center text-sm text-emerald-400">
                  <Check className="h-4 w-4 mr-1" />
                  Connected
                </span>
                <button
                  onClick={handleDisconnectTeams}
                  className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 border border-red-500/30 rounded-lg hover:bg-red-500/10 transition-colors"
                >
                  Disconnect
                </button>
              </>
            ) : teamsIntegration?.is_configured ? (
              <button
                onClick={handleConnectTeams}
                className="px-4 py-2 bg-[#464EB8] text-white rounded-lg hover:bg-[#5258c9] transition-colors flex items-center"
              >
                Connect Teams
                <ExternalLink className="h-4 w-4 ml-2" />
              </button>
            ) : (
              <span className="text-sm text-gray-500">Not configured</span>
            )}
          </div>
        </div>

        {/* Teams Settings (when connected) */}
        {teamsIntegration?.is_connected && (
          <div className="mt-6 pt-6 border-t border-premium-border">
            <button
              onClick={() => {
                setTeamsSettingsOpen(!teamsSettingsOpen)
                if (!teamsSettingsOpen && teamsList.length === 0) {
                  loadTeamsList()
                }
              }}
              className="flex items-center justify-between w-full text-left"
            >
              <span className="flex items-center text-white">
                <Settings className="h-4 w-4 mr-2" />
                Notification Settings
              </span>
              <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${teamsSettingsOpen ? 'rotate-180' : ''}`} />
            </button>

            {teamsSettingsOpen && (
              <div className="mt-4 space-y-4">
                {/* Team Selection */}
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Team</label>
                  <div className="flex space-x-2">
                    <select
                      value={selectedTeam}
                      onChange={(e) => {
                        setSelectedTeam(e.target.value)
                        setTeamsSelectedChannel('')
                        if (e.target.value) {
                          loadTeamsChannels(e.target.value)
                        }
                      }}
                      className="flex-1 bg-premium-surface border border-premium-border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-gold-500"
                    >
                      <option value="">Select a team...</option>
                      {teamsList.map((team) => (
                        <option key={team.id} value={team.id}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={loadTeamsList}
                      disabled={teamsLoading}
                      className="px-3 py-2 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white transition-colors"
                    >
                      <RefreshCw className={`h-4 w-4 ${teamsLoading ? 'animate-spin' : ''}`} />
                    </button>
                  </div>
                </div>

                {/* Channel Selection */}
                {selectedTeam && (
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Channel</label>
                    <div className="flex space-x-2">
                      <select
                        value={teamsSelectedChannel}
                        onChange={(e) => setTeamsSelectedChannel(e.target.value)}
                        className="flex-1 bg-premium-surface border border-premium-border rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-gold-500"
                      >
                        <option value="">Select a channel...</option>
                        {teamsChannels.map((channel) => (
                          <option key={channel.id} value={channel.id}>
                            {channel.name}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={handleTeamsTestMessage}
                        disabled={!teamsSelectedChannel}
                        className="px-4 py-2 bg-gold-500 text-premium-bg rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                      >
                        <Send className="h-4 w-4 mr-2" />
                        Test
                      </button>
                    </div>
                  </div>
                )}

                {/* Notification Types */}
                <div className="space-y-3">
                  <label className="block text-sm text-gray-400">Notification Types</label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.teams.meeting_summaries_enabled}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        teams: { ...prev.teams, meeting_summaries_enabled: e.target.checked }
                      }))}
                      className="w-4 h-4 rounded border-gray-600 text-gold-500 focus:ring-gold-500 bg-premium-surface"
                    />
                    <span className="ml-3 text-white">Meeting Summaries</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.teams.action_item_reminders_enabled}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        teams: { ...prev.teams, action_item_reminders_enabled: e.target.checked }
                      }))}
                      className="w-4 h-4 rounded border-gray-600 text-gold-500 focus:ring-gold-500 bg-premium-surface"
                    />
                    <span className="ml-3 text-white">Action Item Reminders</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={settings.teams.briefing_notifications_enabled}
                      onChange={(e) => setSettings(prev => ({
                        ...prev,
                        teams: { ...prev.teams, briefing_notifications_enabled: e.target.checked }
                      }))}
                      className="w-4 h-4 rounded border-gray-600 text-gold-500 focus:ring-gold-500 bg-premium-surface"
                    />
                    <span className="ml-3 text-white">Pre-Meeting Briefings</span>
                  </label>
                </div>

                <button
                  onClick={handleSaveTeamsSettings}
                  className="px-4 py-2 bg-gold-500 text-premium-bg rounded-lg hover:bg-gold-400 transition-colors"
                >
                  Save Settings
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Help Section */}
      <div className="bg-premium-surface border border-premium-border rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-3">How Integrations Work</h3>
        <div className="space-y-3 text-sm text-gray-400">
          <p>
            <Bell className="h-4 w-4 inline mr-2 text-gold-400" />
            <strong className="text-white">Meeting Summaries:</strong> After each meeting ends, a summary with key points and action items will be posted to your selected channel.
          </p>
          <p>
            <Bell className="h-4 w-4 inline mr-2 text-gold-400" />
            <strong className="text-white">Action Item Reminders:</strong> Get notified about upcoming deadlines for action items assigned during meetings.
          </p>
          <p>
            <Bell className="h-4 w-4 inline mr-2 text-gold-400" />
            <strong className="text-white">Pre-Meeting Briefings:</strong> Receive a briefing before scheduled meetings with participant context and suggested topics.
          </p>
        </div>
      </div>
    </div>
  )
}

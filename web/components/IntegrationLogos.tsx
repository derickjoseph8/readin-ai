'use client'

const integrations = [
  { name: 'Microsoft Teams', logo: '/integrations/teams.svg' },
  { name: 'Zoom', logo: '/integrations/zoom.svg' },
  { name: 'Google Meet', logo: '/integrations/meet.svg' },
  { name: 'Webex', logo: '/integrations/webex.svg' },
  { name: 'Slack', logo: '/integrations/slack.svg' },
  { name: 'Discord', logo: '/integrations/discord.svg' },
  { name: 'Skype', logo: '/integrations/skype.svg' },
  { name: 'GoToMeeting', logo: '/integrations/goto.svg' },
]

export default function IntegrationLogos() {
  return (
    <section className="py-16 px-4">
      <div className="max-w-7xl mx-auto">
        <p className="text-center text-gray-500 mb-8 text-sm uppercase tracking-wider">
          Works seamlessly with your favorite apps
        </p>

        {/* Logo Grid */}
        <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12">
          {integrations.map((integration, index) => (
            <div
              key={index}
              className="group flex flex-col items-center"
            >
              <div className="w-16 h-16 bg-premium-card rounded-xl border border-premium-border flex items-center justify-center group-hover:border-gold-500/30 transition-colors">
                <span className="text-2xl font-bold text-gray-600 group-hover:text-gold-400 transition-colors">
                  {integration.name.charAt(0)}
                </span>
              </div>
              <span className="mt-2 text-xs text-gray-600 group-hover:text-gray-400 transition-colors">
                {integration.name}
              </span>
            </div>
          ))}
        </div>

        <p className="text-center text-gray-600 mt-8 text-sm">
          And <span className="text-gold-400">30+ more</span> video conferencing apps
        </p>
      </div>
    </section>
  )
}

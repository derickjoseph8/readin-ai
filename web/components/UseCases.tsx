'use client'

import { Tv, Users, ClipboardList, Video, Mic2, GraduationCap } from 'lucide-react'

const useCases = [
  {
    icon: Tv,
    title: 'TV & Media Interviews',
    description: 'Glance at key facts and talking points while maintaining eye contact with the camera.',
    gradient: 'from-gold-500 to-gold-600',
  },
  {
    icon: Users,
    title: 'Expert Panels & Q&A',
    description: 'Instant recall of statistics, quotes, and supporting points when put on the spot.',
    gradient: 'from-emerald-500 to-emerald-600',
  },
  {
    icon: ClipboardList,
    title: 'Research Questionnaires',
    description: 'Structured responses for interviews, surveys, and formal research sessions.',
    gradient: 'from-gold-500 to-gold-600',
  },
  {
    icon: Video,
    title: 'Team Meetings',
    description: 'Contribute thoughtfully to discussions on Teams, Zoom, or any video call.',
    gradient: 'from-emerald-500 to-emerald-600',
  },
  {
    icon: Mic2,
    title: 'Podcasts & Webinars',
    description: 'Never get caught off guard by listener questions or unexpected topics.',
    gradient: 'from-gold-500 to-gold-600',
  },
  {
    icon: GraduationCap,
    title: 'Job Interviews',
    description: 'Nail behavioral questions with structured, confident responses every time.',
    gradient: 'from-emerald-500 to-emerald-600',
  },
]

export default function UseCases() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Perfect For{' '}
            <span className="text-gradient-gold">Any Conversation</span>
          </h2>
          <p className="text-xl text-gray-400">
            From high-stakes interviews to everyday meetings, ReadIn AI helps you communicate with confidence.
          </p>
        </div>

        {/* Use Cases Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {useCases.map((useCase, index) => (
            <div
              key={index}
              className="group p-6 bg-premium-card rounded-2xl border border-premium-border hover:border-gold-500/30 hover:-translate-y-1 transition-all duration-300"
            >
              <div className={`w-14 h-14 bg-gradient-to-br ${useCase.gradient} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 group-hover:shadow-gold transition-all duration-300`}>
                <useCase.icon className="h-7 w-7 text-premium-bg" />
              </div>
              <h3 className="text-lg font-semibold mb-2 text-white">{useCase.title}</h3>
              <p className="text-gray-400 text-sm">{useCase.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

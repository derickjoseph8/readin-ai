'use client'

import { Tv, Users, ClipboardList, Video, Mic2, GraduationCap } from 'lucide-react'

const useCases = [
  {
    icon: Tv,
    title: 'TV & Media Interviews',
    description: 'Glance at key facts and talking points while maintaining eye contact with the camera.',
    color: 'bg-red-500/10 text-red-400 border-red-500/20',
  },
  {
    icon: Users,
    title: 'Expert Panels & Q&A',
    description: 'Instant recall of statistics, quotes, and supporting points when put on the spot.',
    color: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  },
  {
    icon: ClipboardList,
    title: 'Research Questionnaires',
    description: 'Structured responses for interviews, surveys, and formal research sessions.',
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  },
  {
    icon: Video,
    title: 'Team Meetings',
    description: 'Contribute thoughtfully to discussions on Teams, Zoom, or any video call.',
    color: 'bg-green-500/10 text-green-400 border-green-500/20',
  },
  {
    icon: Mic2,
    title: 'Podcasts & Webinars',
    description: 'Never get caught off guard by listener questions or unexpected topics.',
    color: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  },
  {
    icon: GraduationCap,
    title: 'Job Interviews',
    description: 'Nail behavioral questions with structured, confident responses every time.',
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
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
            <span className="text-gradient">Any Conversation</span>
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
              className={`p-6 rounded-2xl border ${useCase.color} hover:scale-[1.02] transition-transform cursor-default`}
            >
              <useCase.icon className="h-8 w-8 mb-4" />
              <h3 className="text-lg font-semibold mb-2 text-white">{useCase.title}</h3>
              <p className="text-gray-400 text-sm">{useCase.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

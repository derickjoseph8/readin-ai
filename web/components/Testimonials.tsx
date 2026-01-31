'use client'

import { Star, Quote } from 'lucide-react'

const testimonials = [
  {
    name: 'Sarah Chen',
    role: 'Product Manager',
    company: 'Tech Startup',
    image: '/testimonials/sarah.jpg',
    rating: 5,
    quote: 'ReadIn AI has completely transformed my meeting experience. I used to dread Q&A sessions, but now I feel prepared for any question that comes my way.',
  },
  {
    name: 'Michael Roberts',
    role: 'Sales Director',
    company: 'Enterprise SaaS',
    image: '/testimonials/michael.jpg',
    rating: 5,
    quote: 'The 2-second response time is incredible. My clients think I have photographic memory. Closed 40% more deals since I started using it.',
  },
  {
    name: 'Dr. Emily Watson',
    role: 'Research Scientist',
    company: 'University',
    image: '/testimonials/emily.jpg',
    rating: 5,
    quote: 'As someone who presents at conferences regularly, this tool is invaluable. I can focus on delivery while ReadIn handles the details.',
  },
  {
    name: 'James Park',
    role: 'Executive Coach',
    company: 'Leadership Consulting',
    image: '/testimonials/james.jpg',
    rating: 5,
    quote: 'I recommend ReadIn AI to all my clients. The privacy-first approach means sensitive discussions stay completely confidential.',
  },
  {
    name: 'Lisa Thompson',
    role: 'HR Director',
    company: 'Fortune 500',
    image: '/testimonials/lisa.jpg',
    rating: 5,
    quote: 'Conducting interviews all day used to be exhausting. Now I have instant recall of candidate details and can focus on the conversation.',
  },
  {
    name: 'David Kim',
    role: 'Podcast Host',
    company: 'Tech Talk Daily',
    image: '/testimonials/david.jpg',
    rating: 5,
    quote: 'My guests are always impressed by my preparation. Little do they know, ReadIn AI is my secret weapon for informed, engaging interviews.',
  },
]

export default function Testimonials() {
  return (
    <section className="py-24 px-4 bg-premium-surface/50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center px-4 py-2 bg-gold-500/10 border border-gold-500/30 rounded-full mb-6">
            <Star className="h-4 w-4 text-gold-400 mr-2 fill-gold-400" />
            <span className="text-sm text-gold-300">Loved by professionals</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            What Our Users{' '}
            <span className="text-gradient-gold">Are Saying</span>
          </h2>
          <p className="text-xl text-gray-400">
            Join thousands of professionals who communicate with confidence.
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {testimonials.map((testimonial, index) => (
            <div
              key={index}
              className="group p-6 bg-premium-card rounded-2xl border border-premium-border hover:border-gold-500/30 transition-all duration-300"
            >
              {/* Quote Icon */}
              <div className="mb-4">
                <Quote className="h-8 w-8 text-gold-500/30" />
              </div>

              {/* Quote */}
              <p className="text-gray-300 mb-6 leading-relaxed">
                "{testimonial.quote}"
              </p>

              {/* Rating */}
              <div className="flex mb-4">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <Star key={i} className="h-4 w-4 text-gold-400 fill-gold-400" />
                ))}
              </div>

              {/* Author */}
              <div className="flex items-center">
                <div className="w-12 h-12 bg-gradient-to-br from-gold-500/20 to-emerald-500/20 rounded-full flex items-center justify-center mr-4">
                  <span className="text-lg font-bold text-gold-400">
                    {testimonial.name.split(' ').map(n => n[0]).join('')}
                  </span>
                </div>
                <div>
                  <p className="font-semibold text-white">{testimonial.name}</p>
                  <p className="text-sm text-gray-500">
                    {testimonial.role} at {testimonial.company}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const faqs = [
  {
    question: 'Will people notice I\'m using ReadIn AI?',
    answer: 'No! The overlay is designed for quick glances. The bullet points are meant to be rephrased in your own words, not read verbatim. A brief glance looks just like you\'re thinking — completely natural.',
  },
  {
    question: 'Is my audio sent to the cloud?',
    answer: 'No. Your audio is transcribed locally on your device using the Whisper AI model. Only the transcribed text (not audio) is sent to generate responses, and nothing is stored after your session ends.',
  },
  {
    question: 'Which video conferencing apps are supported?',
    answer: 'ReadIn AI works with Teams, Zoom, Google Meet, Webex, Skype, Discord, Slack, GoToMeeting, BlueJeans, RingCentral, and 30+ other apps. For browser-based meetings like Google Meet, just click "Start Listening" manually.',
  },
  {
    question: 'Does it work on Mac and Linux?',
    answer: 'Yes! ReadIn AI is cross-platform and works on Windows, macOS, and Linux. On macOS, you may need to install a virtual audio driver (like BlackHole) to capture system audio.',
  },
  {
    question: 'What happens after my free trial?',
    answer: 'After 7 days, you can continue with limited free usage (10 responses/day) or upgrade to Premium ($10/month) for unlimited responses. No credit card required to start your trial.',
  },
  {
    question: 'Can I use it for in-person meetings?',
    answer: 'Yes! Just have your laptop nearby with ReadIn AI running. It will pick up audio from the room and provide responses. Works great for interviews, panels, and presentations.',
  },
  {
    question: 'How fast are the responses?',
    answer: 'Typically under 2 seconds from when someone finishes speaking. The transcription happens in real-time, and Claude AI generates concise bullet points almost instantly.',
  },
  {
    question: 'Can I customize the response style?',
    answer: 'Currently, responses are optimized for quick scanning with 2-4 bullet points of 5-10 words each. We\'re working on customization options for future releases.',
  },
]

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <section id="faq" className="py-24 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Frequently Asked{' '}
            <span className="text-gradient">Questions</span>
          </h2>
          <p className="text-xl text-gray-400">
            Everything you need to know about ReadIn AI.
          </p>
        </div>

        {/* FAQ Items */}
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className="bg-dark-900/50 rounded-xl border border-white/10 overflow-hidden"
            >
              <button
                className="w-full px-6 py-4 flex items-center justify-between text-left"
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
              >
                <span className="font-medium pr-4">{faq.question}</span>
                <ChevronDown
                  className={`h-5 w-5 text-gray-400 transition-transform flex-shrink-0 ${
                    openIndex === index ? 'rotate-180' : ''
                  }`}
                />
              </button>
              {openIndex === index && (
                <div className="px-6 pb-4">
                  <p className="text-gray-400">{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

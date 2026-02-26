'use client'

import Link from 'next/link'
import StaticHeader from '@/components/StaticHeader'
import Footer from '@/components/Footer'

export default function PrivacyPolicy() {
  return (
    <>
      <StaticHeader />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-2 text-white">Privacy Policy</h1>
          <p className="text-gray-400 mb-8">Last updated: January 30, 2026</p>

          <div className="prose prose-invert max-w-none space-y-8">
            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">1. Introduction</h2>
              <p className="text-gray-300">
                ReadIn AI (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our desktop application and related services.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">2. Information We Collect</h2>
              <h3 className="text-xl font-medium text-white mb-2">2.1 Information You Provide</h3>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>Account information (email address, name, profession)</li>
                <li>Payment information (processed securely via Stripe)</li>
                <li>Meeting transcriptions and AI-generated responses (when enabled)</li>
                <li>Communication preferences</li>
              </ul>

              <h3 className="text-xl font-medium text-white mb-2 mt-4">2.2 Automatically Collected Information</h3>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>Device information and operating system</li>
                <li>Usage statistics and feature interactions</li>
                <li>Error logs for troubleshooting</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">3. How We Process Audio</h2>
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
                <p className="text-emerald-300 font-medium mb-2">Privacy-First Audio Processing</p>
                <p className="text-gray-300">
                  Your audio is processed locally on your device using OpenAI Whisper. Audio data is never uploaded to our servers. Only the transcribed text (if you choose to save meeting notes) and AI-generated suggestions are stored.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">4. How We Use Your Information</h2>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>To provide and improve our services</li>
                <li>To personalize AI responses based on your profession</li>
                <li>To send meeting summaries and commitment reminders (when enabled)</li>
                <li>To process payments and manage subscriptions</li>
                <li>To communicate important service updates</li>
                <li>To analyze and improve our machine learning models</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">5. Data Storage and Security</h2>
              <p className="text-gray-300">
                We implement industry-standard security measures to protect your data. Meeting data is encrypted both in transit and at rest. You can delete your data at any time through your account settings.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">6. Data Sharing</h2>
              <p className="text-gray-300 mb-4">We do not sell your personal information. We may share data with:</p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li><strong>Service Providers:</strong> Stripe for payments, cloud infrastructure providers</li>
                <li><strong>AI Services:</strong> Anthropic for AI response generation (text only, no audio)</li>
                <li><strong>Legal Requirements:</strong> When required by law or to protect rights</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">7. Your Rights</h2>
              <p className="text-gray-300 mb-4">You have the right to:</p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>Access your personal data</li>
                <li>Correct inaccurate data</li>
                <li>Delete your account and data</li>
                <li>Export your data</li>
                <li>Opt-out of marketing communications</li>
                <li>Disable specific data collection features</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">8. Data Retention</h2>
              <p className="text-gray-300">
                We retain your data as long as your account is active. Meeting data is retained for 90 days by default, or until you delete it. You can adjust retention settings in the app. Upon account deletion, all data is removed within 30 days.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">9. Children&apos;s Privacy</h2>
              <p className="text-gray-300">
                ReadIn AI is not intended for users under 18 years of age. We do not knowingly collect information from children.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">10. Changes to This Policy</h2>
              <p className="text-gray-300">
                We may update this Privacy Policy from time to time. We will notify you of significant changes via email or in-app notification.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">11. Contact Us</h2>
              <p className="text-gray-300">
                If you have questions about this Privacy Policy, please contact us at:
              </p>
              <p className="text-gold-400 mt-2">
                <a href="mailto:privacy@getreadin.ai">privacy@getreadin.ai</a>
              </p>
            </section>
          </div>

          <div className="mt-12 pt-8 border-t border-premium-border">
            <Link href="/" className="text-gold-400 hover:text-gold-300 transition-colors">
              &larr; Back to Home
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}

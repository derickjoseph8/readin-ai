'use client'

import Link from 'next/link'
import StaticHeader from '@/components/StaticHeader'
import Footer from '@/components/Footer'

export default function TermsOfService() {
  return (
    <>
      <StaticHeader />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-2 text-white">Terms of Service</h1>
          <p className="text-gray-400 mb-8">Last updated: January 30, 2026</p>

          <div className="prose prose-invert max-w-none space-y-8">
            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">1. Acceptance of Terms</h2>
              <p className="text-gray-300">
                By accessing or using ReadIn AI (&quot;the Service&quot;), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the Service.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">2. Description of Service</h2>
              <p className="text-gray-300">
                ReadIn AI is a desktop application that provides real-time AI-powered assistance during video calls and meetings. The Service includes transcription, AI-generated talking points, meeting summaries, and other features as described on our website.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">3. Account Registration</h2>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>You must provide accurate and complete information during registration</li>
                <li>You are responsible for maintaining the security of your account</li>
                <li>You must be at least 18 years old to use the Service</li>
                <li>One person or entity may not maintain multiple free accounts</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">4. Subscription and Payments</h2>
              <h3 className="text-xl font-medium text-white mb-2">4.1 Free Trial</h3>
              <p className="text-gray-300 mb-4">
                New users receive a 7-day free trial with 10 AI responses per day. No credit card is required for the trial.
              </p>

              <h3 className="text-xl font-medium text-white mb-2">4.2 Premium Subscription</h3>
              <p className="text-gray-300 mb-4">
                Premium subscription is $29.99/month and includes unlimited AI responses and all features. Subscriptions renew automatically unless cancelled.
              </p>

              <h3 className="text-xl font-medium text-white mb-2">4.3 Corporate Plans</h3>
              <p className="text-gray-300">
                Team, Business, and Enterprise plans are available for organizations. The admin pays for the subscription, and team members join at no additional cost per invite.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">5. Refund Policy</h2>
              <p className="text-gray-300">
                We offer a 30-day money-back guarantee on Premium subscriptions. If you&apos;re not satisfied, contact us within 30 days of purchase for a full refund.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">6. Acceptable Use</h2>
              <p className="text-gray-300 mb-4">You agree not to:</p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>Use the Service for any illegal purpose</li>
                <li>Record or transcribe conversations without proper consent</li>
                <li>Share your account credentials with others</li>
                <li>Attempt to reverse engineer or copy the Service</li>
                <li>Use the Service to generate harmful or misleading content</li>
                <li>Violate any applicable laws or regulations</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">7. Recording Consent</h2>
              <div className="bg-gold-500/10 border border-gold-500/30 rounded-xl p-4">
                <p className="text-gold-300 font-medium mb-2">Important Notice</p>
                <p className="text-gray-300">
                  You are responsible for obtaining proper consent before using ReadIn AI to assist in conversations. Laws regarding recording and transcription vary by jurisdiction. We recommend informing all participants that AI assistance is being used.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">8. Intellectual Property</h2>
              <p className="text-gray-300">
                ReadIn AI and its original content, features, and functionality are owned by ReadIn AI and are protected by international copyright, trademark, and other intellectual property laws. You retain ownership of your meeting data and content.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">9. Limitation of Liability</h2>
              <p className="text-gray-300">
                ReadIn AI is provided &quot;as is&quot; without warranties of any kind. We are not liable for any indirect, incidental, or consequential damages arising from your use of the Service. Our total liability shall not exceed the amount you paid for the Service in the 12 months preceding any claim.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">10. Service Modifications</h2>
              <p className="text-gray-300">
                We reserve the right to modify, suspend, or discontinue any part of the Service at any time. We will provide reasonable notice of significant changes.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">11. Termination</h2>
              <p className="text-gray-300">
                We may terminate or suspend your account at any time for violation of these Terms. Upon termination, your right to use the Service will immediately cease.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">12. Governing Law</h2>
              <p className="text-gray-300">
                These Terms shall be governed by the laws of the State of Delaware, United States, without regard to its conflict of law provisions.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">13. Contact</h2>
              <p className="text-gray-300">
                For questions about these Terms, please contact us at:
              </p>
              <p className="text-gold-400 mt-2">
                <a href="mailto:legal@getreadin.ai">legal@getreadin.ai</a>
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

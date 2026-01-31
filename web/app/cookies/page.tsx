'use client'

import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'

export default function CookiePolicy() {
  return (
    <>
      <Header />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-2 text-white">Cookie Policy</h1>
          <p className="text-gray-400 mb-8">Last updated: January 30, 2026</p>

          <div className="prose prose-invert max-w-none space-y-8">
            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">1. What Are Cookies?</h2>
              <p className="text-gray-300">
                Cookies are small text files stored on your device when you visit our website. They help us provide a better user experience and understand how you interact with our site.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">2. How We Use Cookies</h2>
              <p className="text-gray-300 mb-4">We use cookies for:</p>

              <h3 className="text-xl font-medium text-white mb-2">2.1 Essential Cookies</h3>
              <p className="text-gray-300 mb-4">
                Required for the website to function. These include authentication tokens and session management.
              </p>

              <h3 className="text-xl font-medium text-white mb-2">2.2 Analytics Cookies</h3>
              <p className="text-gray-300 mb-4">
                Help us understand how visitors use our site. We use privacy-focused analytics that don&apos;t track individual users.
              </p>

              <h3 className="text-xl font-medium text-white mb-2">2.3 Preference Cookies</h3>
              <p className="text-gray-300">
                Remember your settings and preferences, such as theme choices and dismissed notifications.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">3. Cookies We Use</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-gray-300 border-collapse">
                  <thead>
                    <tr className="border-b border-premium-border">
                      <th className="text-left py-3 px-4 text-white">Cookie Name</th>
                      <th className="text-left py-3 px-4 text-white">Purpose</th>
                      <th className="text-left py-3 px-4 text-white">Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">auth_token</td>
                      <td className="py-3 px-4">Authentication</td>
                      <td className="py-3 px-4">30 days</td>
                    </tr>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">session_id</td>
                      <td className="py-3 px-4">Session management</td>
                      <td className="py-3 px-4">Session</td>
                    </tr>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">preferences</td>
                      <td className="py-3 px-4">User preferences</td>
                      <td className="py-3 px-4">1 year</td>
                    </tr>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">_analytics</td>
                      <td className="py-3 px-4">Anonymous usage stats</td>
                      <td className="py-3 px-4">1 year</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">4. Third-Party Cookies</h2>
              <p className="text-gray-300 mb-4">We may use the following third-party services that set cookies:</p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li><strong>Stripe:</strong> Payment processing</li>
                <li><strong>Vercel Analytics:</strong> Privacy-focused website analytics</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">5. Managing Cookies</h2>
              <p className="text-gray-300 mb-4">
                You can control cookies through your browser settings. Most browsers allow you to:
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4">
                <li>View what cookies are stored</li>
                <li>Delete individual or all cookies</li>
                <li>Block cookies from specific or all websites</li>
                <li>Set preferences for first-party vs third-party cookies</li>
              </ul>
              <p className="text-gray-300 mt-4">
                Note: Blocking essential cookies may prevent you from using certain features of our service.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">6. Desktop Application</h2>
              <p className="text-gray-300">
                The ReadIn AI desktop application stores authentication tokens and preferences locally on your device. These are not cookies but serve similar purposes. You can clear this data by logging out or uninstalling the application.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">7. Updates to This Policy</h2>
              <p className="text-gray-300">
                We may update this Cookie Policy from time to time. Changes will be posted on this page with an updated revision date.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">8. Contact Us</h2>
              <p className="text-gray-300">
                If you have questions about our use of cookies, please contact us at:
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

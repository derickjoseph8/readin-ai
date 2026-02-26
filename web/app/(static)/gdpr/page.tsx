'use client'

import Link from 'next/link'
import StaticHeader from '@/components/StaticHeader'
import Footer from '@/components/Footer'
import { Shield, Download, Trash2, Eye, Lock, Globe } from 'lucide-react'

export default function GDPR() {
  return (
    <>
      <StaticHeader />
      <main className="pt-24 pb-16 px-4 min-h-screen bg-premium-bg">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center mb-6">
            <div className="w-16 h-16 bg-gold-500/20 rounded-2xl flex items-center justify-center">
              <Globe className="h-8 w-8 text-gold-400" />
            </div>
          </div>
          <h1 className="text-4xl font-bold mb-2 text-white text-center">GDPR Compliance</h1>
          <p className="text-gray-400 mb-8 text-center">Your data rights under the General Data Protection Regulation</p>

          <div className="prose prose-invert max-w-none space-y-8">
            <section className="bg-premium-card border border-premium-border rounded-2xl p-6">
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">Our Commitment</h2>
              <p className="text-gray-300">
                ReadIn AI is fully committed to GDPR compliance. We respect your privacy rights and have implemented robust measures to protect your personal data. This page explains your rights and how we handle data for users in the European Economic Area (EEA).
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">Your Rights Under GDPR</h2>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-premium-card border border-premium-border rounded-xl p-5">
                  <div className="flex items-center mb-3">
                    <Eye className="h-5 w-5 text-gold-400 mr-2" />
                    <h3 className="font-semibold text-white">Right to Access</h3>
                  </div>
                  <p className="text-gray-400 text-sm">
                    You can request a copy of all personal data we hold about you. We&apos;ll provide this within 30 days.
                  </p>
                </div>

                <div className="bg-premium-card border border-premium-border rounded-xl p-5">
                  <div className="flex items-center mb-3">
                    <Trash2 className="h-5 w-5 text-gold-400 mr-2" />
                    <h3 className="font-semibold text-white">Right to Erasure</h3>
                  </div>
                  <p className="text-gray-400 text-sm">
                    You can request deletion of your personal data. We&apos;ll remove it within 30 days, unless legally required to retain it.
                  </p>
                </div>

                <div className="bg-premium-card border border-premium-border rounded-xl p-5">
                  <div className="flex items-center mb-3">
                    <Download className="h-5 w-5 text-gold-400 mr-2" />
                    <h3 className="font-semibold text-white">Right to Portability</h3>
                  </div>
                  <p className="text-gray-400 text-sm">
                    You can export your data in a machine-readable format to transfer to another service.
                  </p>
                </div>

                <div className="bg-premium-card border border-premium-border rounded-xl p-5">
                  <div className="flex items-center mb-3">
                    <Lock className="h-5 w-5 text-gold-400 mr-2" />
                    <h3 className="font-semibold text-white">Right to Restrict</h3>
                  </div>
                  <p className="text-gray-400 text-sm">
                    You can request that we limit how we process your data in certain circumstances.
                  </p>
                </div>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">Legal Basis for Processing</h2>
              <p className="text-gray-300 mb-4">We process your data based on:</p>
              <ul className="space-y-3">
                <li className="flex items-start">
                  <span className="w-2 h-2 bg-gold-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  <div>
                    <strong className="text-white">Contract Performance:</strong>
                    <span className="text-gray-300"> Processing necessary to provide our services to you</span>
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="w-2 h-2 bg-gold-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  <div>
                    <strong className="text-white">Legitimate Interests:</strong>
                    <span className="text-gray-300"> Improving our services and ensuring security</span>
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="w-2 h-2 bg-gold-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  <div>
                    <strong className="text-white">Consent:</strong>
                    <span className="text-gray-300"> For optional features like marketing emails</span>
                  </div>
                </li>
                <li className="flex items-start">
                  <span className="w-2 h-2 bg-gold-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  <div>
                    <strong className="text-white">Legal Obligation:</strong>
                    <span className="text-gray-300"> When required by law (e.g., financial records)</span>
                  </div>
                </li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">Data Transfers</h2>
              <p className="text-gray-300">
                Your data may be processed in the United States. We ensure adequate protection through:
              </p>
              <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4 mt-4">
                <li>Standard Contractual Clauses approved by the European Commission</li>
                <li>Working only with service providers who maintain appropriate safeguards</li>
                <li>Encryption in transit and at rest</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">Data Retention</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-gray-300 border-collapse">
                  <thead>
                    <tr className="border-b border-premium-border">
                      <th className="text-left py-3 px-4 text-white">Data Type</th>
                      <th className="text-left py-3 px-4 text-white">Retention Period</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">Account Information</td>
                      <td className="py-3 px-4">Until account deletion + 30 days</td>
                    </tr>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">Meeting Transcriptions</td>
                      <td className="py-3 px-4">90 days (configurable)</td>
                    </tr>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">AI Response History</td>
                      <td className="py-3 px-4">90 days (configurable)</td>
                    </tr>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">Payment Records</td>
                      <td className="py-3 px-4">7 years (legal requirement)</td>
                    </tr>
                    <tr className="border-b border-premium-border/50">
                      <td className="py-3 px-4">Usage Analytics</td>
                      <td className="py-3 px-4">2 years (anonymized)</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">How to Exercise Your Rights</h2>
              <div className="bg-premium-card border border-gold-500/30 rounded-xl p-6">
                <p className="text-gray-300 mb-4">
                  To exercise any of your GDPR rights, you can:
                </p>
                <ul className="list-disc list-inside text-gray-300 space-y-2 ml-4 mb-4">
                  <li>Use the data management tools in your account settings</li>
                  <li>Email us at <a href="mailto:privacy@getreadin.ai" className="text-gold-400 hover:text-gold-300">privacy@getreadin.ai</a></li>
                  <li>Use the contact form on our website</li>
                </ul>
                <p className="text-gray-300">
                  We will respond to your request within 30 days. If we need more time, we will inform you of the reason and extension period.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">Supervisory Authority</h2>
              <p className="text-gray-300">
                If you believe we have not adequately addressed your concerns, you have the right to lodge a complaint with your local data protection authority. For users in the EU, you can find your supervisory authority at the European Data Protection Board website.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-semibold text-gold-400 mb-4">Data Protection Officer</h2>
              <p className="text-gray-300">
                For GDPR-related inquiries, please contact our Data Protection team:
              </p>
              <p className="text-gold-400 mt-2">
                <a href="mailto:dpo@getreadin.ai">dpo@getreadin.ai</a>
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

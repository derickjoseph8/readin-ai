'use client'

import Link from 'next/link'
import { Twitter, Github, Linkedin, Mail, Send } from 'lucide-react'
import { useState } from 'react'

export default function Footer() {
  const [email, setEmail] = useState('')

  return (
    <footer className="py-16 px-4 border-t border-premium-border bg-premium-bg">
      <div className="max-w-7xl mx-auto">
        {/* Newsletter Section */}
        <div className="mb-16 p-8 bg-gradient-to-r from-gold-500/10 to-emerald-500/10 rounded-2xl border border-gold-500/20">
          <div className="max-w-2xl mx-auto text-center">
            <h3 className="text-2xl font-bold mb-2 text-white">Stay Updated</h3>
            <p className="text-gray-400 mb-6">Get the latest updates, tips, and exclusive offers delivered to your inbox.</p>
            <form className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="flex-1 px-4 py-3 bg-premium-surface border border-premium-border rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50 transition-colors"
              />
              <button
                type="submit"
                className="px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-xl hover:shadow-gold transition-all flex items-center justify-center"
              >
                <Send className="h-4 w-4 mr-2" />
                Subscribe
              </button>
            </form>
          </div>
        </div>

        <div className="grid md:grid-cols-5 gap-12 mb-12">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link href="/" className="flex items-center space-x-2 mb-4 group">
              <div className="w-9 h-9 bg-gradient-to-br from-gold-400 to-gold-600 rounded-lg flex items-center justify-center shadow-gold-sm group-hover:shadow-gold transition-shadow">
                <span className="text-premium-bg font-bold text-lg">R</span>
              </div>
              <span className="text-xl font-bold text-white">ReadIn <span className="text-gold-400">AI</span></span>
            </Link>
            <p className="text-gray-400 text-sm mb-6 max-w-xs">
              Your AI-powered meeting intelligence platform. Sound brilliant in every meeting.
            </p>
            <div className="flex space-x-3">
              <a href="https://twitter.com/getreadinai" target="_blank" rel="noopener noreferrer" className="w-10 h-10 bg-premium-surface rounded-lg flex items-center justify-center text-gray-400 hover:text-gold-400 hover:bg-premium-card transition-all">
                <Twitter className="h-5 w-5" />
              </a>
              <a href="https://github.com/readinai" target="_blank" rel="noopener noreferrer" className="w-10 h-10 bg-premium-surface rounded-lg flex items-center justify-center text-gray-400 hover:text-gold-400 hover:bg-premium-card transition-all">
                <Github className="h-5 w-5" />
              </a>
              <a href="https://linkedin.com/company/readinai" target="_blank" rel="noopener noreferrer" className="w-10 h-10 bg-premium-surface rounded-lg flex items-center justify-center text-gray-400 hover:text-gold-400 hover:bg-premium-card transition-all">
                <Linkedin className="h-5 w-5" />
              </a>
              <a href="mailto:support@getreadin.ai" className="w-10 h-10 bg-premium-surface rounded-lg flex items-center justify-center text-gray-400 hover:text-gold-400 hover:bg-premium-card transition-all">
                <Mail className="h-5 w-5" />
              </a>
            </div>
          </div>

          {/* Product */}
          <div>
            <h4 className="font-semibold mb-4 text-white">Product</h4>
            <ul className="space-y-3 text-gray-400">
              <li><a href="/#features" className="hover:text-gold-400 transition-colors">Features</a></li>
              <li><a href="/#pricing" className="hover:text-gold-400 transition-colors">Pricing</a></li>
              <li><Link href="/download" className="hover:text-gold-400 transition-colors">Download</Link></li>
              <li><Link href="/changelog" className="hover:text-gold-400 transition-colors">Changelog</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="font-semibold mb-4 text-white">Support</h4>
            <ul className="space-y-3 text-gray-400">
              <li><a href="/#faq" className="hover:text-gold-400 transition-colors">FAQ</a></li>
              <li><Link href="/docs" className="hover:text-gold-400 transition-colors">Documentation</Link></li>
              <li><Link href="/contact" className="hover:text-gold-400 transition-colors">Contact Us</Link></li>
              <li><a href="https://www.getreadin.us/health" target="_blank" rel="noopener noreferrer" className="hover:text-gold-400 transition-colors">System Status</a></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-semibold mb-4 text-white">Legal</h4>
            <ul className="space-y-3 text-gray-400">
              <li><Link href="/privacy" className="hover:text-gold-400 transition-colors">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-gold-400 transition-colors">Terms of Service</Link></li>
              <li><Link href="/cookies" className="hover:text-gold-400 transition-colors">Cookie Policy</Link></li>
              <li><Link href="/gdpr" className="hover:text-gold-400 transition-colors">GDPR</Link></li>
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="pt-8 border-t border-premium-border flex flex-col md:flex-row items-center justify-between text-sm text-gray-500">
          <p>&copy; {new Date().getFullYear()} ReadIn AI. All rights reserved.</p>
          <p className="mt-4 md:mt-0">
            Made with <span className="text-gold-400">AI</span> for humans who want to sound brilliant.
          </p>
        </div>
      </div>
    </footer>
  )
}

'use client';

import Link from 'next/link';
import { Home, ArrowLeft, Search, HelpCircle } from 'lucide-react';

export default function NotFound() {
  return (
    <html lang="en">
      <body className="bg-premium-bg text-white antialiased min-h-screen flex items-center justify-center">
        <div className="max-w-2xl mx-auto px-6 py-16 text-center">
          {/* 404 Icon */}
          <div className="mb-8">
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gold-500/10 border border-gold-500/30">
              <Search className="w-12 h-12 text-gold-500" aria-hidden="true" />
            </div>
          </div>

          {/* Error Message */}
          <h1 className="text-6xl font-bold text-gold-500 mb-4">404</h1>
          <h2 className="text-2xl font-semibold mb-4">Page Not Found</h2>
          <p className="text-gray-400 mb-8 max-w-md mx-auto">
            Sorry, we couldn&apos;t find the page you&apos;re looking for.
            It might have been moved, deleted, or never existed.
          </p>

          {/* Navigation Options */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Link
              href="/"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gold-500 hover:bg-gold-600 text-premium-bg font-semibold rounded-lg transition-colors min-h-[44px] min-w-[44px]"
              aria-label="Go to homepage"
            >
              <Home className="w-5 h-5" aria-hidden="true" />
              Go to Homepage
            </Link>
            <button
              onClick={() => window.history.back()}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-gold-500/30 hover:border-gold-500 text-gold-500 font-semibold rounded-lg transition-colors min-h-[44px] min-w-[44px]"
              aria-label="Go back to previous page"
            >
              <ArrowLeft className="w-5 h-5" aria-hidden="true" />
              Go Back
            </button>
          </div>

          {/* Helpful Links */}
          <div className="border-t border-gray-800 pt-8">
            <h3 className="text-lg font-medium mb-4">Helpful Links</h3>
            <nav className="flex flex-wrap justify-center gap-6" aria-label="Helpful links">
              <Link
                href="/pricing"
                className="text-gray-400 hover:text-gold-500 transition-colors inline-flex items-center gap-2 min-h-[44px]"
                aria-label="View pricing plans"
              >
                Pricing
              </Link>
              <Link
                href="/download"
                className="text-gray-400 hover:text-gold-500 transition-colors inline-flex items-center gap-2 min-h-[44px]"
                aria-label="Download the app"
              >
                Download
              </Link>
              <Link
                href="/about"
                className="text-gray-400 hover:text-gold-500 transition-colors inline-flex items-center gap-2 min-h-[44px]"
                aria-label="Learn about us"
              >
                About
              </Link>
              <Link
                href="/contact"
                className="text-gray-400 hover:text-gold-500 transition-colors inline-flex items-center gap-2 min-h-[44px]"
                aria-label="Contact support"
              >
                <HelpCircle className="w-4 h-4" aria-hidden="true" />
                Contact Support
              </Link>
            </nav>
          </div>
        </div>
      </body>
    </html>
  );
}

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import LanguageSwitcher from './LanguageSwitcher';

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const t = useTranslations('header');
  const tc = useTranslations('common');

  // Check if we're on the homepage
  const isHomePage = pathname === '/' || pathname === '';

  // Helper to get correct href for section links
  const getSectionHref = (section: string) => {
    return isHomePage ? `#${section}` : `/#${section}`;
  };

  // Helper to check if a link is active
  const isActive = (href: string) => {
    // For login and download pages
    if (href === '/login') return pathname === '/login';
    if (href === '/download') return pathname === '/download';
    // For section links, they're not "pages" so don't mark as current
    return false;
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-premium-bg/80 backdrop-blur-xl border-b border-premium-border">
      {/* Announcement bar */}
      <div className="bg-gradient-to-r from-gold-600/20 via-gold-500/20 to-gold-600/20 border-b border-gold-500/20">
        <div className="max-w-7xl mx-auto px-4 py-2">
          <p className="text-center text-sm text-gold-300">
            <Sparkles className="inline h-4 w-4 mr-1" />
            <span className="font-medium">Limited Time:</span> 7-day free trial for new users
          </p>
        </div>
      </div>

      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 group">
            <div className="w-9 h-9 bg-gradient-to-br from-gold-400 to-gold-600 rounded-lg flex items-center justify-center shadow-gold-sm group-hover:shadow-gold transition-shadow">
              <span className="text-premium-bg font-bold text-lg">R</span>
            </div>
            <span className="text-xl font-bold text-white">ReadIn <span className="text-gold-400">AI</span></span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <Link href={getSectionHref('features')} className="text-gray-400 hover:text-gold-400 transition-colors">{t('features')}</Link>
            <Link href={getSectionHref('how-it-works')} className="text-gray-400 hover:text-gold-400 transition-colors">How It Works</Link>
            <Link href={getSectionHref('pricing')} className="text-gray-400 hover:text-gold-400 transition-colors">{t('pricing')}</Link>
            <Link href={getSectionHref('faq')} className="text-gray-400 hover:text-gold-400 transition-colors">FAQ</Link>
          </div>

          {/* CTA Buttons & Language Switcher */}
          <div className="hidden md:flex items-center space-x-4">
            <LanguageSwitcher />
            <Link
              href="/login"
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              aria-current={isActive('/login') ? 'page' : undefined}
            >
              {tc('login')}
            </Link>
            <Link
              href="/download"
              className="px-5 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all hover:-translate-y-0.5"
              aria-current={isActive('/download') ? 'page' : undefined}
            >
              {t('download')}
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 text-gray-400 hover:text-white min-w-[44px] min-h-[44px] flex items-center justify-center"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-premium-border animate-fade-in">
            <div className="flex flex-col space-y-2">
              <Link
                href={getSectionHref('features')}
                className="py-3 px-2 text-gray-400 hover:text-gold-400 transition-colors min-h-[44px] flex items-center"
                onClick={() => setMobileMenuOpen(false)}
              >
                {t('features')}
              </Link>
              <Link
                href={getSectionHref('how-it-works')}
                className="py-3 px-2 text-gray-400 hover:text-gold-400 transition-colors min-h-[44px] flex items-center"
                onClick={() => setMobileMenuOpen(false)}
              >
                How It Works
              </Link>
              <Link
                href={getSectionHref('pricing')}
                className="py-3 px-2 text-gray-400 hover:text-gold-400 transition-colors min-h-[44px] flex items-center"
                onClick={() => setMobileMenuOpen(false)}
              >
                {t('pricing')}
              </Link>
              <Link
                href={getSectionHref('faq')}
                className="py-3 px-2 text-gray-400 hover:text-gold-400 transition-colors min-h-[44px] flex items-center"
                onClick={() => setMobileMenuOpen(false)}
              >
                FAQ
              </Link>
              <div className="py-3 px-2">
                <LanguageSwitcher />
              </div>
              <Link
                href="/login"
                className="py-3 px-4 text-gold-400 hover:text-gold-300 transition-colors min-h-[48px] flex items-center justify-center bg-premium-surface rounded-lg border border-premium-border"
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive('/login') ? 'page' : undefined}
              >
                {tc('login')}
              </Link>
              <Link
                href="/download"
                className="py-3 px-5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg text-center min-h-[48px] flex items-center justify-center"
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive('/download') ? 'page' : undefined}
              >
                {t('download')}
              </Link>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}

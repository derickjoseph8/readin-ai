'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, X, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import LanguageSwitcher from './LanguageSwitcher';

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const t = useTranslations('header');
  const tc = useTranslations('common');

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-premium-bg/80 backdrop-blur-xl border-b border-premium-border">
      {/* Announcement bar */}
      <div className="bg-gradient-to-r from-gold-600/20 via-gold-500/20 to-gold-600/20 border-b border-gold-500/20">
        <div className="max-w-7xl mx-auto px-4 py-2">
          <p className="text-center text-sm text-gold-300">
            <Sparkles className="inline h-4 w-4 mr-1" />
            <span className="font-medium">Limited Time:</span> Extended 14-day free trial for new users
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
            <a href="#features" className="text-gray-400 hover:text-gold-400 transition-colors">{t('features')}</a>
            <a href="#how-it-works" className="text-gray-400 hover:text-gold-400 transition-colors">How It Works</a>
            <a href="#pricing" className="text-gray-400 hover:text-gold-400 transition-colors">{t('pricing')}</a>
            <a href="#faq" className="text-gray-400 hover:text-gold-400 transition-colors">FAQ</a>
          </div>

          {/* CTA Buttons & Language Switcher */}
          <div className="hidden md:flex items-center space-x-4">
            <LanguageSwitcher />
            <Link href="/login" className="px-4 py-2 text-gray-400 hover:text-white transition-colors">
              {tc('login')}
            </Link>
            <Link
              href="/download"
              className="px-5 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all hover:-translate-y-0.5"
            >
              {t('download')}
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden text-gray-400 hover:text-white"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-premium-border animate-fade-in">
            <div className="flex flex-col space-y-4">
              <a href="#features" className="text-gray-400 hover:text-gold-400 transition-colors" onClick={() => setMobileMenuOpen(false)}>{t('features')}</a>
              <a href="#how-it-works" className="text-gray-400 hover:text-gold-400 transition-colors" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
              <a href="#pricing" className="text-gray-400 hover:text-gold-400 transition-colors" onClick={() => setMobileMenuOpen(false)}>{t('pricing')}</a>
              <a href="#faq" className="text-gray-400 hover:text-gold-400 transition-colors" onClick={() => setMobileMenuOpen(false)}>FAQ</a>
              <div className="py-2">
                <LanguageSwitcher />
              </div>
              <Link
                href="/login"
                className="text-gray-400 hover:text-gold-400 transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                {tc('login')}
              </Link>
              <Link
                href="/download"
                className="px-5 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg text-center"
                onClick={() => setMobileMenuOpen(false)}
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

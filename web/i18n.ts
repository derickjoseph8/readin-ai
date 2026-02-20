/**
 * i18n Configuration for ReadIn AI
 * Supports English, Spanish, Swahili, French, German, Portuguese, and Japanese locales
 */

import { getRequestConfig } from 'next-intl/server';

export const locales = ['en', 'es', 'sw', 'fr', 'de', 'pt', 'ja'] as const;
export const defaultLocale = 'en' as const;

export type Locale = (typeof locales)[number];

export const localeNames: Record<Locale, string> = {
  en: 'English',
  es: 'Español',
  sw: 'Kiswahili',
  fr: 'Français',
  de: 'Deutsch',
  pt: 'Português',
  ja: '日本語'
};

export const localeFlags: Record<Locale, string> = {
  en: '🇺🇸',
  es: '🇪🇸',
  sw: '🇰🇪',
  fr: '🇫🇷',
  de: '🇩🇪',
  pt: '🇧🇷',
  ja: '🇯🇵'
};

export default getRequestConfig(async ({ locale }) => {
  // Validate the locale from the request (middleware sets this)
  // For routes where middleware doesn't run (static routes), use default locale
  const validLocale = locale && locales.includes(locale as Locale) ? locale : defaultLocale;
  return {
    locale: validLocale,
    messages: (await import(`./messages/${validLocale}.json`)).default
  };
});

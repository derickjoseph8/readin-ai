/**
 * i18n Configuration for ReadIn AI
 * Supports English, Spanish, and Swahili locales
 */

import { getRequestConfig } from 'next-intl/server';

export const locales = ['en', 'es', 'sw'] as const;
export const defaultLocale = 'en' as const;

export type Locale = (typeof locales)[number];

export const localeNames: Record<Locale, string> = {
  en: 'English',
  es: 'Español',
  sw: 'Kiswahili'
};

export const localeFlags: Record<Locale, string> = {
  en: '🇺🇸',
  es: '🇪🇸',
  sw: '🇰🇪'
};

export default getRequestConfig(async ({ requestLocale }) => {
  const locale = await requestLocale || defaultLocale;
  return {
    locale,
    messages: (await import(`./messages/${locale}.json`)).default
  };
});

/**
 * Next.js Middleware for i18n locale detection and routing
 */

import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from './i18n';

export default createMiddleware({
  // A list of all locales that are supported
  locales,

  // Used when no locale matches
  defaultLocale,

  // Don't redirect to default locale (keep URL clean)
  localePrefix: 'as-needed'
});

export const config = {
  // Match routes that need locale detection
  matcher: [
    // Root path
    '/',
    // Locale-prefixed paths
    '/(en|es|sw|fr|de|pt|ja)/:path*'
  ]
};

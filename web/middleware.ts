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
  // Match ONLY the internationalized locale routes
  // All static pages, auth pages, and other non-i18n routes are excluded
  matcher: [
    // Only match paths that start with a locale prefix
    '/(en|es|sw|fr|de|pt|ja)/:path*'
  ]
};

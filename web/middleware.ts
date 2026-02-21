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
  // Match all paths except static files and API routes
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)'
  ]
};

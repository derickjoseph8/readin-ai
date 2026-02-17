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
  // Match all pathnames except for static files, API routes, etc.
  matcher: [
    // Match all pathnames except for
    // - … if they start with /api, /_next, /_vercel, /static, /favicon.ico, /robots.txt
    // - … static legal/info pages (terms, privacy, cookies, gdpr, docs, changelog, contact)
    // - … admin pages and dashboard support pages (they don't use i18n)
    // - … if they contain a dot (.) - files with extensions
    '/((?!api|_next|_vercel|static|favicon.ico|robots.txt|terms|privacy|cookies|gdpr|docs|changelog|contact|admin|dashboard|login|sso|.*\\..*).*)'
  ]
};

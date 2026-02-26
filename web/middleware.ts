/**
 * Next.js Middleware for i18n locale detection and routing
 * Handles both locale-aware routes and static routes
 */

import createMiddleware from 'next-intl/middleware';
import { NextRequest, NextResponse } from 'next/server';
import { locales, defaultLocale } from './i18n';

// Static routes that should NOT have locale redirection
const STATIC_ROUTES = [
  '/admin',
  '/login',
  '/signup',
  '/dashboard',
  '/download',
  '/pricing',
  '/about',
  '/terms',
  '/contact',
  '/cookies',
  '/gdpr',
  '/privacy',
  '/forgot-password',
  '/reset-password',
  '/verify-email',
  '/docs',
  '/changelog',
  '/sso',
];

// Create the next-intl middleware
const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'as-needed'
});

export default function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Check if this is a static route (or starts with a static route path)
  const isStaticRoute = STATIC_ROUTES.some(route =>
    pathname === route || pathname.startsWith(route + '/')
  );

  if (isStaticRoute) {
    // For static routes, just pass through without locale handling
    // The root layout provides NextIntlClientProvider with default locale
    return NextResponse.next();
  }

  // For all other routes, use the next-intl middleware
  return intlMiddleware(request);
}

export const config = {
  // Match all paths except static files and API routes
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)'
  ]
};

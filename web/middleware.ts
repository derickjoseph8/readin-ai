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

  // Run intl middleware for all routes to provide locale context
  // For static routes, we still need locale context for components using useTranslations
  const response = intlMiddleware(request);

  // For static routes, ensure we don't redirect to locale-prefixed URLs
  if (isStaticRoute) {
    const redirectLocation = response.headers.get('location');
    // If intl middleware is trying to redirect to a locale-prefixed URL, don't allow it
    if (redirectLocation && locales.some(loc => redirectLocation.includes(`/${loc}/`))) {
      return NextResponse.next();
    }
  }

  return response;
}

export const config = {
  // Match all paths except static files and API routes
  matcher: [
    '/((?!api|_next|_vercel|.*\\..*).*)'
  ]
};

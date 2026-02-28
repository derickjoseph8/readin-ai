'use client';

import Link from 'next/link';
import { ChevronRight, Home } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  current?: boolean;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  showHome?: boolean;
  className?: string;
}

/**
 * Accessible breadcrumb navigation component.
 *
 * Usage:
 * ```tsx
 * <Breadcrumbs
 *   items={[
 *     { label: 'Dashboard', href: '/dashboard' },
 *     { label: 'Settings', href: '/dashboard/settings' },
 *     { label: 'Billing', current: true }
 *   ]}
 * />
 * ```
 */
export default function Breadcrumbs({
  items,
  showHome = true,
  className = ''
}: BreadcrumbsProps) {
  const allItems: BreadcrumbItem[] = showHome
    ? [{ label: 'Home', href: '/' }, ...items]
    : items;

  return (
    <nav
      aria-label="Breadcrumb"
      className={`flex items-center space-x-1 text-sm ${className}`}
    >
      <ol
        className="flex items-center space-x-1"
        itemScope
        itemType="https://schema.org/BreadcrumbList"
      >
        {allItems.map((item, index) => {
          const isLast = index === allItems.length - 1;
          const isHome = index === 0 && showHome;

          return (
            <li
              key={index}
              className="flex items-center"
              itemScope
              itemProp="itemListElement"
              itemType="https://schema.org/ListItem"
            >
              {index > 0 && (
                <ChevronRight
                  className="w-4 h-4 text-gray-500 mx-1 flex-shrink-0"
                  aria-hidden="true"
                />
              )}

              {item.href && !item.current ? (
                <Link
                  href={item.href}
                  className="inline-flex items-center gap-1 text-gray-400 hover:text-gold-500 transition-colors min-h-[44px] px-1"
                  itemProp="item"
                  aria-label={isHome ? 'Go to home page' : `Go to ${item.label}`}
                >
                  {isHome && (
                    <Home className="w-4 h-4" aria-hidden="true" />
                  )}
                  <span itemProp="name">{isHome ? '' : item.label}</span>
                  <meta itemProp="position" content={String(index + 1)} />
                </Link>
              ) : (
                <span
                  className={`inline-flex items-center gap-1 min-h-[44px] px-1 ${
                    item.current ? 'text-gold-500 font-medium' : 'text-gray-400'
                  }`}
                  aria-current={item.current ? 'page' : undefined}
                  itemProp="name"
                >
                  {item.label}
                  <meta itemProp="position" content={String(index + 1)} />
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/**
 * Simple hook to generate breadcrumbs from pathname.
 */
export function useBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean);

  return segments.map((segment, index) => {
    const href = '/' + segments.slice(0, index + 1).join('/');
    const isLast = index === segments.length - 1;

    // Format segment label
    const label = segment
      .replace(/-/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());

    return {
      label,
      href: isLast ? undefined : href,
      current: isLast,
    };
  });
}

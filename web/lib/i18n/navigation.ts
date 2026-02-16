/**
 * i18n Navigation helpers for ReadIn AI
 */

import { createSharedPathnamesNavigation } from 'next-intl/navigation';
import { locales } from '@/i18n';

export const { Link, redirect, usePathname, useRouter } =
  createSharedPathnamesNavigation({ locales });

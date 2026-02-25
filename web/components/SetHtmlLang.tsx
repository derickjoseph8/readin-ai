'use client';

import { useEffect } from 'react';

interface SetHtmlLangProps {
  locale: string;
}

/**
 * Component that dynamically sets the lang attribute on the html element.
 * This is necessary because the root layout renders the html tag with a static lang,
 * but locale-specific routes need to update it based on the current locale.
 */
export default function SetHtmlLang({ locale }: SetHtmlLangProps) {
  useEffect(() => {
    // Update the html lang attribute when the locale changes
    document.documentElement.lang = locale;

    // Also set the dir attribute for RTL languages if needed in the future
    // For now, all supported locales are LTR
    document.documentElement.dir = 'ltr';
  }, [locale]);

  // This component doesn't render anything
  return null;
}

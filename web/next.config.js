/** @type {import('next').NextConfig} */
const createNextIntlPlugin = require('next-intl/plugin');

const withNextIntl = createNextIntlPlugin('./i18n.ts');

const nextConfig = {
  images: {
    unoptimized: true,
  },
  // Handle trailing slashes for cleaner URLs
  trailingSlash: false,
  // Force dynamic rendering for i18n
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
}

module.exports = withNextIntl(nextConfig);

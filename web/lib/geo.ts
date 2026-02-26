// Geo-detection utility for regional pricing

export type Region = 'global' | 'western';

// Countries that get $19.99 pricing (Africa, UAE, Asia)
const GLOBAL_REGIONS = [
  // Africa
  'KE', 'NG', 'ZA', 'GH', 'TZ', 'UG', 'RW', 'ET', 'EG', 'MA', 'DZ', 'TN', 'SN', 'CI', 'CM', 'AO', 'MZ', 'ZW', 'BW', 'NA', 'MW', 'ZM', 'MU',
  // Middle East / UAE
  'AE', 'SA', 'QA', 'KW', 'BH', 'OM', 'JO', 'LB', 'IQ', 'IR', 'PK',
  // Asia
  'IN', 'BD', 'LK', 'NP', 'MM', 'TH', 'VN', 'ID', 'MY', 'PH', 'SG', 'CN', 'JP', 'KR', 'TW', 'HK',
];

// Countries that get $29.99 pricing (Europe, North America)
const WESTERN_REGIONS = [
  // North America
  'US', 'CA', 'MX',
  // Europe
  'GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'CH', 'SE', 'NO', 'DK', 'FI', 'IE', 'PT', 'PL', 'CZ', 'HU', 'RO', 'BG', 'GR', 'HR', 'SK', 'SI', 'LT', 'LV', 'EE',
  // Oceania
  'AU', 'NZ',
];

export interface GeoData {
  country: string;
  countryCode: string;
  region: Region;
  currency: string;
  price: number;
  annualPrice: number;
}

export async function detectRegion(): Promise<GeoData> {
  try {
    // Use ip-api.com (free, no API key required, 45 requests/minute)
    const response = await fetch('http://ip-api.com/json/?fields=countryCode,country', {
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error('Geo API failed');
    }

    const data = await response.json();
    const countryCode = data.countryCode || 'US';
    const country = data.country || 'United States';

    const isGlobalRegion = GLOBAL_REGIONS.includes(countryCode);

    return {
      country,
      countryCode,
      region: isGlobalRegion ? 'global' : 'western',
      currency: isGlobalRegion ? 'USD' : 'USD',
      price: isGlobalRegion ? 19.99 : 29.99,
      annualPrice: isGlobalRegion ? 199.90 : 299.90,
    };
  } catch (error) {
    // Default to western pricing if geo detection fails
    return {
      country: 'United States',
      countryCode: 'US',
      region: 'western',
      currency: 'USD',
      price: 29.99,
      annualPrice: 299.90,
    };
  }
}

export function getRegionFromCountryCode(countryCode: string): Region {
  return GLOBAL_REGIONS.includes(countryCode) ? 'global' : 'western';
}

export function getPricing(region: Region) {
  if (region === 'global') {
    return {
      individual: { monthly: 19.99, annual: 199.90 },
      team: { monthly: 14.99, annual: 149.90 },
      growth: { monthly: 9.99, annual: 99.90 },
      savings: 'Save $40 (2 months free)',
    };
  }
  return {
    individual: { monthly: 29.99, annual: 299.90 },
    team: { monthly: 19.99, annual: 199.90 },
    growth: { monthly: 14.99, annual: 149.90 },
    savings: 'Save $60 (2 months free)',
  };
}

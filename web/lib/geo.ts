// Geo-detection utility for regional pricing

export type Region = 'global' | 'western';

// Countries that get global pricing (Africa, UAE, Asia)
const GLOBAL_REGIONS = [
  // Africa
  'KE', 'NG', 'ZA', 'GH', 'TZ', 'UG', 'RW', 'ET', 'EG', 'MA', 'DZ', 'TN', 'SN', 'CI', 'CM', 'AO', 'MZ', 'ZW', 'BW', 'NA', 'MW', 'ZM', 'MU',
  // Middle East / UAE
  'AE', 'SA', 'QA', 'KW', 'BH', 'OM', 'JO', 'LB', 'IQ', 'IR', 'PK',
  // Asia
  'IN', 'BD', 'LK', 'NP', 'MM', 'TH', 'VN', 'ID', 'MY', 'PH', 'SG', 'CN', 'JP', 'KR', 'TW', 'HK',
];

export interface GeoData {
  country: string;
  countryCode: string;
  region: Region;
}

export async function detectRegion(): Promise<GeoData> {
  try {
    // Try multiple geo APIs for reliability
    const apis = [
      'https://ipapi.co/json/',
      'https://api.ipify.org?format=json',
    ];

    // Try ipapi.co first (more reliable, includes country)
    const response = await fetch('https://ipapi.co/json/', {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      const data = await response.json();
      const countryCode = data.country_code || data.country || 'US';
      const country = data.country_name || 'United States';
      const isGlobalRegion = GLOBAL_REGIONS.includes(countryCode);

      return {
        country,
        countryCode,
        region: isGlobalRegion ? 'global' : 'western',
      };
    }

    throw new Error('Primary geo API failed');
  } catch (error) {
    // Fallback: try to detect from timezone
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const isAfricaOrAsia = timezone.startsWith('Africa/') ||
                             timezone.startsWith('Asia/') ||
                             timezone.includes('Dubai') ||
                             timezone.includes('Nairobi') ||
                             timezone.includes('Lagos') ||
                             timezone.includes('Johannesburg');

      return {
        country: 'Unknown',
        countryCode: 'XX',
        region: isAfricaOrAsia ? 'global' : 'western',
      };
    } catch {
      // Default to western pricing if all detection fails
      return {
        country: 'United States',
        countryCode: 'US',
        region: 'western',
      };
    }
  }
}

export function getRegionFromCountryCode(countryCode: string): Region {
  return GLOBAL_REGIONS.includes(countryCode) ? 'global' : 'western';
}

// Pricing configuration - used by frontend and synced with backend
export const PRICING_CONFIG = {
  global: {
    individual: { monthly: 19.99, annual: 199.90 },
    starter: { monthly: 14.99, annual: 149.90, minSeats: 2, maxSeats: 9 },
    team: { monthly: 12.99, annual: 129.90, minSeats: 10, maxSeats: 50 },
    enterprise: { monthly: 9.99, annual: 99.90, minSeats: 50 }, // Hidden from UI
  },
  western: {
    individual: { monthly: 29.99, annual: 299.90 },
    starter: { monthly: 24.99, annual: 249.90, minSeats: 2, maxSeats: 9 },
    team: { monthly: 19.99, annual: 199.90, minSeats: 10, maxSeats: 50 },
    enterprise: { monthly: 14.99, annual: 149.90, minSeats: 50 }, // Hidden from UI
  },
};

export function getPricing(region: Region, plan: keyof typeof PRICING_CONFIG.global, isAnnual: boolean = false) {
  const regionPricing = PRICING_CONFIG[region];
  const planPricing = regionPricing[plan];
  return isAnnual ? planPricing.annual : planPricing.monthly;
}

export function calculateTeamBilling(region: Region, seats: number, isAnnual: boolean = false) {
  let plan: 'starter' | 'team' | 'enterprise';

  if (seats >= 50) {
    plan = 'enterprise';
  } else if (seats >= 10) {
    plan = 'team';
  } else {
    plan = 'starter';
  }

  const pricePerUser = getPricing(region, plan, isAnnual);
  const totalMonthly = pricePerUser * seats;
  const totalAnnual = isAnnual ? totalMonthly : totalMonthly * 10; // 2 months free

  return {
    plan,
    seats,
    pricePerUser,
    totalMonthly: isAnnual ? totalMonthly / 10 : totalMonthly,
    totalAnnual,
    isEnterprise: seats >= 50,
  };
}

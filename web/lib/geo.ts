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
  // Try multiple IP geolocation APIs in sequence for reliability
  const geoApis = [
    {
      url: 'https://ipapi.co/json/',
      parseResponse: (data: any) => ({
        countryCode: data.country_code || data.country,
        country: data.country_name,
      }),
    },
    {
      url: 'https://ipwho.is/',
      parseResponse: (data: any) => ({
        countryCode: data.country_code,
        country: data.country,
      }),
    },
    {
      url: 'https://api.country.is/',
      parseResponse: (data: any) => ({
        countryCode: data.country,
        country: data.country,
      }),
    },
    {
      url: 'https://freeipapi.com/api/json/',
      parseResponse: (data: any) => ({
        countryCode: data.countryCode,
        country: data.countryName,
      }),
    },
  ];

  // Try each API until one works
  for (const api of geoApis) {
    try {
      const response = await fetch(api.url, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3000), // 3 second timeout per API
      });

      if (response.ok) {
        const data = await response.json();
        const parsed = api.parseResponse(data);

        if (parsed.countryCode) {
          const countryCode = parsed.countryCode.toUpperCase();
          const isGlobalRegion = GLOBAL_REGIONS.includes(countryCode);

          return {
            country: parsed.country || countryCode,
            countryCode,
            region: isGlobalRegion ? 'global' : 'western',
          };
        }
      }
    } catch {
      // Continue to next API
      continue;
    }
  }

  // Fallback: detect from timezone (more reliable than giving up)
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    // Map common African/Asian timezones to regions
    const globalTimezones = [
      'Africa/', 'Asia/', 'Indian/',
      'Dubai', 'Nairobi', 'Lagos', 'Johannesburg', 'Cairo', 'Casablanca',
      'Kolkata', 'Mumbai', 'Delhi', 'Karachi', 'Dhaka', 'Bangkok', 'Singapore',
      'Hong_Kong', 'Shanghai', 'Tokyo', 'Seoul', 'Manila', 'Jakarta',
    ];

    const isGlobalTimezone = globalTimezones.some(tz => timezone.includes(tz));

    return {
      country: 'Detected via timezone',
      countryCode: isGlobalTimezone ? 'XX-GLOBAL' : 'XX-WESTERN',
      region: isGlobalTimezone ? 'global' : 'western',
    };
  } catch {
    // Ultimate fallback: western pricing
    return {
      country: 'United States',
      countryCode: 'US',
      region: 'western',
    };
  }
}

export function getRegionFromCountryCode(countryCode: string): Region {
  return GLOBAL_REGIONS.includes(countryCode) ? 'global' : 'western';
}

// Pricing configuration - used by frontend and synced with backend
export const PRICING_CONFIG = {
  global: {
    individual: { monthly: 19.99, annual: 199.90 },
    starter: { monthly: 14.99, annual: 149.90, minSeats: 3, maxSeats: 9 },
    team: { monthly: 12.99, annual: 129.90, minSeats: 10, maxSeats: 50 },
    enterprise: { monthly: 9.99, annual: 99.90, minSeats: 50 }, // Hidden from UI
  },
  western: {
    individual: { monthly: 29.99, annual: 299.90 },
    starter: { monthly: 24.99, annual: 249.90, minSeats: 3, maxSeats: 9 },
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

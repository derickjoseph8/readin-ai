'use client';

import { useState, useEffect } from 'react';
import { CreditCard, Check, Sparkles, Calendar, ExternalLink, Users, Building2, Zap, Shield, Clock, HeadphonesIcon } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/hooks/useAuth';
import { detectRegion, type Region, PRICING_CONFIG } from '@/lib/geo';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us';

// Declare PaystackPop type
declare global {
  interface Window {
    PaystackPop: {
      setup: (options: {
        key: string
        email: string
        amount: number
        currency: string
        ref: string
        metadata?: Record<string, unknown>
        onClose?: () => void
        callback?: (response: { reference: string }) => void
      }) => {
        openIframe: () => void
      }
    }
  }
}

// Helper to load Paystack script
const loadPaystackScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    if (typeof window !== 'undefined' && window.PaystackPop) {
      resolve()
      return
    }

    const existingScript = document.querySelector('script[src="https://js.paystack.co/v1/inline.js"]')
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve())
      return
    }

    const script = document.createElement('script')
    script.src = 'https://js.paystack.co/v1/inline.js'
    script.async = false
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load payment system'))
    document.head.appendChild(script)
  })
}

// Dynamic pricing tiers based on detected region
function getPricingTiers(region: Region) {
  const prices = PRICING_CONFIG[region];

  return {
    individual: [
      {
        name: 'Free',
        price: 0,
        period: 'forever',
        description: 'For trying out ReadIn AI',
        features: [
          '5 AI responses per day',
          'Basic meeting transcription',
          'Standard AI suggestions',
          'Email support',
        ],
        limitations: [
          'No meeting summaries',
          'No team features',
        ],
        cta: 'Current Plan',
        highlighted: false,
      },
      {
        name: 'Premium Monthly',
        price: prices.individual.monthly,
        period: '/month',
        description: 'For professionals who want more',
        features: [
          'Unlimited AI responses',
          'Advanced GPT-4 integration',
          'Meeting summaries & action items',
          'Interview coaching',
          'Priority support',
          'Export to PDF/Word',
        ],
        limitations: [],
        cta: 'Upgrade to Premium',
        highlighted: true,
        priceId: 'price_premium_monthly',
      },
      {
        name: 'Premium Annual',
        price: prices.individual.annual,
        period: '/year',
        description: '2 months free with annual billing',
        features: [
          'Everything in Premium',
          `Save $${((prices.individual.monthly * 12) - prices.individual.annual).toFixed(0)} per year`,
          'Priority feature requests',
        ],
        limitations: [],
        cta: 'Save with Annual',
        highlighted: false,
        priceId: 'price_premium_annual',
      },
    ],
    business: [
      {
        name: 'Starter Monthly',
        price: prices.starter.monthly,
        period: '/user/month',
        description: '3-9 users (3 seats minimum)',
        features: [
          'Everything in Premium',
          '3 mandatory seats included',
          'Up to 9 team members',
          'Team analytics dashboard',
          'Admin controls',
        ],
        limitations: [],
        cta: 'Sign Up',
        highlighted: true,
        priceId: 'price_starter_monthly',
      },
      {
        name: 'Starter Annual',
        price: prices.starter.annual,
        period: '/user/year',
        description: '2 months free - 3 seats minimum',
        features: [
          'Everything in Starter Monthly',
          `Save $${((prices.starter.monthly * 12) - prices.starter.annual).toFixed(0)}/user per year`,
          '3-9 team members',
        ],
        limitations: [],
        cta: 'Sign Up',
        highlighted: false,
        priceId: 'price_starter_annual',
      },
      {
        name: 'Team',
        price: prices.team.monthly,
        period: '/user/month',
        description: 'For teams of 10-50 users',
        features: [
          'Everything in Starter',
          '10-50 team members',
          'Volume discount applied',
          'Advanced analytics',
          'API access',
          'SAML SSO',
        ],
        limitations: [],
        cta: 'Sign Up',
        highlighted: false,
        priceId: 'price_team_monthly',
      },
      {
        name: 'Team Annual',
        price: prices.team.annual,
        period: '/user/year',
        description: '2 months free for 10-50 users',
        features: [
          'Everything in Team Monthly',
          `Save $${((prices.team.monthly * 12) - prices.team.annual).toFixed(0)}/user per year`,
          'Best value for mid-size teams',
        ],
        limitations: [],
        cta: 'Sign Up',
        highlighted: false,
        priceId: 'price_team_annual',
      },
      {
        name: 'Enterprise',
        price: null,
        period: 'Custom',
        description: 'For 51+ users with volume discounts',
        features: [
          'Everything in Team',
          'Unlimited team members',
          'Best volume pricing',
          'Custom deployment',
          'SLA guarantees',
          'On-premise option',
          'Dedicated success manager',
          '2 months free on annual',
        ],
        limitations: [],
        cta: 'Contact Sales',
        highlighted: false,
      },
    ],
  };
}

export default function BillingPage() {
  const { user, status, token } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'individual' | 'business'>(
    user?.account_type === 'business' ? 'business' : 'individual'
  );
  const [region, setRegion] = useState<Region>('western');
  const [pricingLoaded, setPricingLoaded] = useState(false);
  const [paystackLoaded, setPaystackLoaded] = useState(false);
  const t = useTranslations('settings.billing');

  // Load Paystack script immediately on mount
  useEffect(() => {
    loadPaystackScript()
      .then(() => setPaystackLoaded(true))
      .catch((err) => console.error('Paystack load error:', err))
  }, [])

  // Detect region for pricing on mount
  useEffect(() => {
    detectRegion()
      .then((geoData) => {
        setRegion(geoData.region);
      })
      .catch(() => {
        setRegion('western'); // Default fallback
      })
      .finally(() => {
        setPricingLoaded(true);
      });
  }, []);

  // Get pricing tiers based on detected region
  const pricingTiers = getPricingTiers(region);

  const handleUpgrade = async (priceId?: string) => {
    if (!token || !priceId) return;
    setIsLoading(true);

    try {
      // Ensure Paystack is loaded before proceeding
      if (!window.PaystackPop) {
        await loadPaystackScript();
      }

      // Parse priceId to determine plan and billing period
      // Format: price_premium_monthly, price_starter_annual, etc.
      const parts = priceId.replace('price_', '').split('_');
      const planName = parts[0]; // premium, starter, team
      const isAnnual = parts[1] === 'annual';

      // Map plan names
      const plan = planName === 'premium' ? 'individual' : planName;

      // Default seats based on plan
      const seats = plan === 'individual' ? 1 : plan === 'starter' ? 3 : 10;

      // Get popup data from backend
      const response = await fetch(`${API_URL}/api/v1/payments/paystack/popup`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plan,
          seats,
          is_annual: isAnnual
        })
      });

      const popupData = await response.json();

      if (!response.ok) {
        throw new Error(popupData.detail || 'Failed to initialize payment');
      }

      // Double-check Paystack is available
      if (!window.PaystackPop) {
        throw new Error('Payment system failed to load. Please refresh and try again.');
      }

      const handler = window.PaystackPop.setup({
        key: popupData.key,
        email: popupData.email,
        amount: popupData.amount,
        currency: popupData.currency,
        ref: popupData.ref,
        metadata: popupData.metadata,
        onClose: () => {
          setIsLoading(false);
        },
        callback: async (response: { reference: string }) => {
          // Verify payment on backend
          try {
            const verifyResponse = await fetch(
              `${API_URL}/api/v1/payments/paystack/verify/${response.reference}`,
              {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
              }
            );

            if (verifyResponse.ok) {
              alert('Payment successful! Your account has been upgraded.');
              window.location.reload();
            } else {
              alert('Payment verification failed. Please contact support.');
            }
          } catch (err) {
            console.error('Verification error:', err);
            alert('Payment verification failed. Please contact support.');
          } finally {
            setIsLoading(false);
          }
        },
      });

      handler.openIframe();
    } catch (error) {
      console.error('Failed to create checkout:', error);
      alert(error instanceof Error ? error.message : 'Failed to create checkout session. Please try again.');
      setIsLoading(false);
    }
  };

  const handleManageBilling = async () => {
    if (!token) return;
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/subscription/manage`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await response.json();
      if (data.portal_url) {
        window.location.href = data.portal_url;
      }
    } catch (error) {
      console.error('Failed to open billing portal:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleContactSales = () => {
    window.location.href = '/contact?type=sales';
  };

  const isPremium = status?.subscription.status === 'active';
  const isTrial = status?.subscription.status === 'trial';
  const isBusinessAccount = user?.account_type === 'business';

  const currentTiers = pricingTiers[selectedTab];

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">{t('title')}</h1>
        <p className="text-gray-400 mt-1">
          Choose the plan that fits your needs
        </p>
      </div>

      {/* Current Status Banner */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                isPremium ? 'bg-gold-500/20' : isTrial ? 'bg-blue-500/20' : 'bg-gray-500/20'
              }`}>
                {isPremium ? (
                  <Sparkles className="h-5 w-5 text-gold-400" />
                ) : isTrial ? (
                  <Clock className="h-5 w-5 text-blue-400" />
                ) : (
                  <Zap className="h-5 w-5 text-gray-400" />
                )}
              </div>
              <div>
                <p className="text-lg font-semibold text-white">
                  {isPremium ? 'Premium Plan' : isTrial ? 'Free Trial' : 'Free Plan'}
                </p>
                <p className="text-sm text-gray-400">
                  {isPremium && 'You have access to all premium features'}
                  {isTrial && `${status?.subscription.trial_days_remaining} days remaining in trial`}
                  {!isPremium && !isTrial && 'Upgrade to unlock all features'}
                </p>
              </div>
            </div>
          </div>

          {isPremium && (
            <button
              onClick={handleManageBilling}
              disabled={isLoading}
              className="flex items-center px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white hover:border-gold-500/30 transition-colors"
            >
              Manage Billing
              <ExternalLink className="h-4 w-4 ml-2" />
            </button>
          )}
        </div>

        {isPremium && status?.subscription.current_period_end && (
          <div className="mt-4 pt-4 border-t border-premium-border flex items-center text-gray-400 text-sm">
            <Calendar className="h-4 w-4 mr-2" />
            Next billing: {new Date(status.subscription.current_period_end).toLocaleDateString()}
          </div>
        )}
      </div>

      {/* Plan Type Toggle */}
      <div className="flex justify-center">
        <div className="inline-flex bg-premium-surface rounded-lg p-1">
          <button
            onClick={() => setSelectedTab('individual')}
            className={`flex items-center px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
              selectedTab === 'individual'
                ? 'bg-gold-500 text-premium-bg'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Users className="h-4 w-4 mr-2" />
            Individual
          </button>
          <button
            onClick={() => setSelectedTab('business')}
            className={`flex items-center px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
              selectedTab === 'business'
                ? 'bg-gold-500 text-premium-bg'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Building2 className="h-4 w-4 mr-2" />
            Business
          </button>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className={`grid gap-6 ${selectedTab === 'individual' ? 'md:grid-cols-3' : 'md:grid-cols-3'}`}>
        {currentTiers.map((tier) => (
          <div
            key={tier.name}
            className={`relative bg-premium-card border rounded-xl p-6 ${
              tier.highlighted
                ? 'border-gold-500 shadow-gold'
                : 'border-premium-border'
            }`}
          >
            {tier.highlighted && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="px-3 py-1 bg-gold-500 text-premium-bg text-xs font-semibold rounded-full">
                  Most Popular
                </span>
              </div>
            )}

            <div className="mb-6">
              <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{tier.description}</p>
            </div>

            <div className="mb-6">
              {tier.price !== null ? (
                <div className="flex items-baseline">
                  <span className="text-3xl font-bold text-white">${tier.price}</span>
                  <span className="text-gray-500 ml-1">{tier.period}</span>
                </div>
              ) : (
                <div className="text-3xl font-bold text-white">{tier.period}</div>
              )}
            </div>

            <ul className="space-y-3 mb-6">
              {tier.features.map((feature, idx) => (
                <li key={idx} className="flex items-start text-sm">
                  <Check className="h-4 w-4 text-emerald-400 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-300">{feature}</span>
                </li>
              ))}
              {tier.limitations?.map((limitation, idx) => (
                <li key={idx} className="flex items-start text-sm">
                  <span className="h-4 w-4 text-gray-600 mr-2 mt-0.5 flex-shrink-0">—</span>
                  <span className="text-gray-500">{limitation}</span>
                </li>
              ))}
            </ul>

            <button
              onClick={() => {
                if (tier.cta === 'Contact Sales') {
                  handleContactSales();
                } else if (tier.priceId) {
                  handleUpgrade(tier.priceId);
                }
              }}
              disabled={isLoading || (!tier.priceId && tier.cta !== 'Contact Sales')}
              className={`w-full py-3 rounded-lg font-medium transition-all ${
                tier.highlighted
                  ? 'bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg hover:shadow-gold'
                  : tier.priceId || tier.cta === 'Contact Sales'
                  ? 'bg-premium-surface border border-premium-border text-white hover:border-gold-500/30'
                  : 'bg-premium-surface border border-premium-border text-gray-500 cursor-not-allowed'
              }`}
            >
              {tier.cta}
            </button>
          </div>
        ))}
      </div>

      {/* Business Features */}
      {selectedTab === 'business' && (
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Enterprise Features</h3>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="flex items-start">
              <Shield className="h-5 w-5 text-gold-400 mr-3 mt-0.5" />
              <div>
                <p className="font-medium text-white">SSO Integration</p>
                <p className="text-sm text-gray-500">SAML, OAuth, Azure AD, Okta</p>
              </div>
            </div>
            <div className="flex items-start">
              <Users className="h-5 w-5 text-gold-400 mr-3 mt-0.5" />
              <div>
                <p className="font-medium text-white">Team Management</p>
                <p className="text-sm text-gray-500">Roles, permissions, analytics</p>
              </div>
            </div>
            <div className="flex items-start">
              <HeadphonesIcon className="h-5 w-5 text-gold-400 mr-3 mt-0.5" />
              <div>
                <p className="font-medium text-white">Dedicated Support</p>
                <p className="text-sm text-gray-500">24/7 priority support</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* FAQ */}
      <div className="bg-premium-surface border border-premium-border rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Billing FAQ</h3>
        <div className="space-y-4">
          <div>
            <p className="font-medium text-white">Can I cancel anytime?</p>
            <p className="text-sm text-gray-400 mt-1">
              Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your billing period.
            </p>
          </div>
          <div>
            <p className="font-medium text-white">What payment methods do you accept?</p>
            <p className="text-sm text-gray-400 mt-1">
              We accept all major credit cards (Visa, Mastercard, Amex) and PayPal through our secure payment provider Stripe.
            </p>
          </div>
          <div>
            <p className="font-medium text-white">Do you offer refunds?</p>
            <p className="text-sm text-gray-400 mt-1">
              We offer a 14-day money-back guarantee. If you're not satisfied, contact us for a full refund.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { CreditCard, Check, Sparkles, Calendar, ExternalLink } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/hooks/useAuth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us';

export default function BillingPage() {
  const { user, status, token } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const t = useTranslations('settings.billing');
  const tp = useTranslations('pricing');

  const handleUpgrade = async () => {
    if (!token) return;
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/stripe/create-checkout`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ price_id: 'price_monthly' })
      });

      const data = await response.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (error) {
      console.error('Failed to create checkout:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleManageBilling = async () => {
    if (!token) return;
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/stripe/customer-portal`, {
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

  const isPremium = status?.subscription.status === 'active';
  const isTrial = status?.subscription.status === 'trial';

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">{t('title')}</h1>
        <p className="text-gray-400 mt-1">
          Manage your subscription and payment method
        </p>
      </div>

      {/* Current Plan */}
      <div className="bg-premium-card border border-premium-border rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">{t('currentPlan')}</h2>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-white">
                {isPremium ? 'Premium' : isTrial ? 'Trial' : 'Free'}
              </span>
              {isPremium && (
                <span className="px-2 py-0.5 bg-gold-500/20 text-gold-400 text-xs rounded-full">
                  Active
                </span>
              )}
              {isTrial && (
                <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                  {status?.subscription.trial_days_remaining} days left
                </span>
              )}
            </div>

            <ul className="mt-4 space-y-2">
              {isPremium || isTrial ? (
                <>
                  <li className="flex items-center text-gray-400 text-sm">
                    <Check className="h-4 w-4 text-emerald-400 mr-2" />
                    Unlimited AI responses
                  </li>
                  <li className="flex items-center text-gray-400 text-sm">
                    <Check className="h-4 w-4 text-emerald-400 mr-2" />
                    Advanced GPT-4 integration
                  </li>
                  <li className="flex items-center text-gray-400 text-sm">
                    <Check className="h-4 w-4 text-emerald-400 mr-2" />
                    Meeting summaries & action items
                  </li>
                  <li className="flex items-center text-gray-400 text-sm">
                    <Check className="h-4 w-4 text-emerald-400 mr-2" />
                    Priority support
                  </li>
                </>
              ) : (
                <>
                  <li className="flex items-center text-gray-400 text-sm">
                    <Check className="h-4 w-4 text-gray-600 mr-2" />
                    5 meetings per month
                  </li>
                  <li className="flex items-center text-gray-400 text-sm">
                    <Check className="h-4 w-4 text-gray-600 mr-2" />
                    Basic AI suggestions
                  </li>
                </>
              )}
            </ul>
          </div>

          <div className="text-right">
            {isPremium && (
              <>
                <p className="text-3xl font-bold text-white">$19</p>
                <p className="text-gray-500 text-sm">/month</p>
              </>
            )}
            {isTrial && (
              <p className="text-gold-400 font-medium">Free Trial</p>
            )}
            {!isPremium && !isTrial && (
              <p className="text-gray-400 font-medium">Free</p>
            )}
          </div>
        </div>

        {/* Next billing date */}
        {isPremium && status?.subscription.current_period_end && (
          <div className="mt-6 pt-4 border-t border-premium-border flex items-center text-gray-400 text-sm">
            <Calendar className="h-4 w-4 mr-2" />
            {t('nextBilling')}: {new Date(status.subscription.current_period_end).toLocaleDateString()}
          </div>
        )}
      </div>

      {/* Upgrade CTA */}
      {!isPremium && (
        <div className="bg-gradient-to-r from-gold-600/20 to-gold-500/10 border border-gold-500/30 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <Sparkles className="h-6 w-6 text-gold-400" />
            <h2 className="text-lg font-semibold text-white">
              {isTrial ? 'Upgrade Before Trial Ends' : 'Upgrade to Premium'}
            </h2>
          </div>

          <p className="text-gray-400 mb-4">
            Unlock unlimited AI responses, advanced features, and priority support.
          </p>

          <button
            onClick={handleUpgrade}
            disabled={isLoading}
            className="px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-semibold rounded-lg hover:shadow-gold transition-all disabled:opacity-50"
          >
            {isLoading ? 'Loading...' : tp('pro.cta')}
          </button>
        </div>
      )}

      {/* Manage Billing */}
      {isPremium && (
        <div className="bg-premium-card border border-premium-border rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">{t('paymentMethod')}</h2>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-premium-surface rounded-lg flex items-center justify-center">
                <CreditCard className="h-5 w-5 text-gray-400" />
              </div>
              <div>
                <p className="text-white">**** **** **** 4242</p>
                <p className="text-gray-500 text-sm">Expires 12/25</p>
              </div>
            </div>

            <button
              onClick={handleManageBilling}
              disabled={isLoading}
              className="flex items-center px-4 py-2 bg-premium-surface border border-premium-border rounded-lg text-gray-400 hover:text-white hover:border-gold-500/30 transition-colors disabled:opacity-50"
            >
              {t('updateCard')}
              <ExternalLink className="h-4 w-4 ml-2" />
            </button>
          </div>

          <button
            onClick={handleManageBilling}
            disabled={isLoading}
            className="mt-4 text-sm text-gray-500 hover:text-red-400 transition-colors"
          >
            {t('cancel')}
          </button>
        </div>
      )}
    </div>
  );
}

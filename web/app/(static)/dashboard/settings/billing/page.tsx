'use client'

import { useState, useEffect } from 'react'
import {
  CreditCard,
  Check,
  Zap,
  Crown,
  ExternalLink,
  Calendar,
  AlertCircle,
  Lock,
  FileText,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import { usePermissions } from '@/lib/hooks/usePermissions'
import { paymentsApi, Invoice, PaymentMethod, SubscriptionStatus } from '@/lib/api/payments'

// Collapsible Section Component for mobile
function CollapsibleSection({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
  className = ''
}: {
  title: string
  icon?: React.ElementType
  children: React.ReactNode
  defaultOpen?: boolean
  className?: string
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className={`bg-premium-card border border-premium-border rounded-xl overflow-hidden ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 sm:px-6 py-4 flex items-center justify-between text-left touch-manipulation min-h-[56px]"
      >
        <div className="flex items-center">
          {Icon && <Icon className="h-5 w-5 text-gold-400 mr-2 sm:mr-3" />}
          <h2 className="font-semibold text-white text-sm sm:text-base">{title}</h2>
        </div>
        <div className="p-1">
          {isOpen ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </button>
      {isOpen && (
        <div className="px-4 sm:px-6 pb-4 sm:pb-6 pt-0">
          {children}
        </div>
      )}
    </div>
  )
}

const plans = [
  {
    id: 'free',
    name: 'Free Trial',
    price: 0,
    period: 'for 7 days',
    features: [
      '10 AI responses per day',
      'All video conferencing apps',
      'Real-time transcription',
      'Profession-tailored responses',
    ],
    cta: 'Current Plan',
    current: true,
  },
  {
    id: 'premium',
    name: 'Premium',
    price: 29.99,
    period: 'per month',
    features: [
      'Unlimited AI responses',
      'Profession-specific knowledge base',
      'Smart meeting notes emailed to you',
      'Action item & commitment tracking',
      'Pre-meeting briefings & context',
      'Participant memory across meetings',
      'Priority support',
    ],
    cta: 'Upgrade to Premium',
    popular: true,
  },
  {
    id: 'team',
    name: 'Team',
    price: 19.99,
    period: 'per user/month',
    features: [
      'Everything in Premium',
      '5 seats included',
      'Team admin dashboard',
      'Shared meeting insights',
      'Centralized billing',
    ],
    cta: 'Upgrade to Team',
  },
]

export default function BillingPage() {
  const { status } = useAuth()
  const { permissions } = usePermissions()
  const [isLoading, setIsLoading] = useState<string | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([])
  const [subscriptionDetails, setSubscriptionDetails] = useState<SubscriptionStatus | null>(null)
  const [loadingInvoices, setLoadingInvoices] = useState(false)

  const currentPlan = status?.subscription.status === 'active' ? 'premium' :
                      status?.subscription.status === 'trial' ? 'trial' : 'free'

  // Check if user can manage billing (org admins or non-org users)
  const canManageBilling = permissions.canManageOrgBilling

  // Fetch billing data on mount
  useEffect(() => {
    if (canManageBilling) {
      fetchBillingData()
    }
  }, [canManageBilling])

  const fetchBillingData = async () => {
    setLoadingInvoices(true)
    try {
      const [invoicesData, methodsData, subData] = await Promise.all([
        paymentsApi.getInvoices(5),
        paymentsApi.getPaymentMethods(),
        paymentsApi.getSubscriptionStatus(),
      ])
      setInvoices(invoicesData)
      setPaymentMethods(methodsData)
      setSubscriptionDetails(subData)
    } catch (error) {
      console.error('Failed to fetch billing data:', error)
    } finally {
      setLoadingInvoices(false)
    }
  }

  const handleUpgrade = async (planId: string) => {
    if (!canManageBilling) return
    setIsLoading(planId)
    try {
      const data = await paymentsApi.createCheckout()
      if (data.checkout_url) {
        window.location.href = data.checkout_url
      }
    } catch (error) {
      console.error('Upgrade failed:', error)
    } finally {
      setIsLoading(null)
    }
  }

  const handleManageSubscription = async () => {
    if (!canManageBilling) return

    try {
      const data = await paymentsApi.getBillingPortal()
      if (data.portal_url) {
        window.location.href = data.portal_url
      }
    } catch (error) {
      console.error('Portal access failed:', error)
    }
  }

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will retain access until the end of your billing period.')) {
      return
    }

    try {
      await paymentsApi.cancelSubscription()
      fetchBillingData()
    } catch (error) {
      console.error('Cancel failed:', error)
    }
  }

  const handleReactivate = async () => {
    try {
      await paymentsApi.reactivateSubscription()
      fetchBillingData()
    } catch (error) {
      console.error('Reactivate failed:', error)
    }
  }

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount / 100)
  }

  // Show restricted access message for org members who can't manage billing
  if (!canManageBilling) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Billing & Subscription</h1>
          <p className="text-gray-400 mt-1">
            Manage your subscription and billing information
          </p>
        </div>

        {/* Restricted Access Notice */}
        <div className="bg-premium-card border border-premium-border rounded-xl p-8 text-center">
          <div className="w-16 h-16 bg-gold-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="h-8 w-8 text-gold-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Billing Access Restricted</h2>
          <p className="text-gray-400 max-w-md mx-auto mb-6">
            Only organization administrators can manage billing and subscription settings.
            Please contact your organization admin to make changes.
          </p>

          {/* Show current status read-only */}
          <div className="bg-premium-surface rounded-lg p-4 max-w-sm mx-auto">
            <div className="flex items-center justify-between">
              <span className="text-gray-400 text-sm">Current Plan</span>
              <span className="text-white font-medium capitalize">
                {currentPlan === 'trial' ? 'Pro Trial' : currentPlan}
              </span>
            </div>
            {status?.subscription.status === 'trial' && status.subscription.trial_days_remaining && (
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-premium-border">
                <span className="text-gray-400 text-sm">Trial Remaining</span>
                <span className="text-gold-400 text-sm">
                  {status.subscription.trial_days_remaining} days
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="px-1">
        <h1 className="text-xl sm:text-2xl font-bold text-white">Billing & Subscription</h1>
        <p className="text-gray-400 mt-1 text-sm sm:text-base">
          Manage your subscription and billing information
        </p>
      </div>

      {/* Current Subscription Status */}
      <CollapsibleSection title="Current Subscription" icon={Crown} defaultOpen={true}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <span className="text-lg sm:text-xl font-bold text-white capitalize">
                {currentPlan === 'trial' ? 'Pro Trial' : currentPlan}
              </span>
              {status?.subscription.status === 'active' && (
                <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                  Active
                </span>
              )}
              {status?.subscription.status === 'trial' && (
                <span className="px-2 py-1 bg-gold-500/20 text-gold-400 text-xs rounded-full">
                  Trial
                </span>
              )}
            </div>

            {status?.subscription.status === 'trial' && status.subscription.trial_days_remaining && (
              <p className="text-gray-400 text-sm mt-2 flex items-center">
                <Calendar className="h-4 w-4 mr-1.5 flex-shrink-0" />
                {status.subscription.trial_days_remaining} days remaining in trial
              </p>
            )}

            {status?.subscription.current_period_end && (
              <p className="text-gray-400 text-sm mt-1.5 flex items-center">
                <Calendar className="h-4 w-4 mr-1.5 flex-shrink-0" />
                Renews on {new Date(status.subscription.current_period_end).toLocaleDateString()}
              </p>
            )}
          </div>

          {status?.subscription.status === 'active' && (
            <button
              onClick={handleManageSubscription}
              className="w-full sm:w-auto px-4 py-3 border border-premium-border text-gray-300 rounded-lg hover:bg-premium-surface transition-colors flex items-center justify-center text-sm min-h-[48px] touch-manipulation"
            >
              Manage Subscription
              <ExternalLink className="h-4 w-4 ml-2" />
            </button>
          )}
        </div>

        {/* Usage Stats */}
        {status?.usage && (
          <div className="mt-5 pt-5 border-t border-premium-border">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">Today&apos;s Usage</span>
              <span className="text-white text-sm">
                {status.usage.daily_count || 0}
                {status.usage.daily_limit && ` / ${status.usage.daily_limit}`} responses
              </span>
            </div>
            <div className="h-2.5 sm:h-2 bg-premium-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full"
                style={{
                  width: status.usage.daily_limit
                    ? `${Math.min((status.usage.daily_count / status.usage.daily_limit) * 100, 100)}%`
                    : '0%'
                }}
              />
            </div>
          </div>
        )}
      </CollapsibleSection>

      {/* Trial Warning */}
      {status?.subscription.status === 'trial' && status.subscription.trial_days_remaining && status.subscription.trial_days_remaining <= 3 && (
        <div className="bg-gold-500/10 border border-gold-500/30 rounded-xl p-4 flex items-start">
          <AlertCircle className="h-5 w-5 text-gold-400 mr-3 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-white font-medium text-sm sm:text-base">Your trial is ending soon</p>
            <p className="text-gold-400/80 text-xs sm:text-sm mt-1">
              Upgrade now to keep your unlimited access and all Pro features.
            </p>
          </div>
        </div>
      )}

      {/* Plans */}
      <div>
        <h2 className="font-semibold text-white mb-4 px-1 text-sm sm:text-base">Available Plans</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`bg-premium-card border rounded-xl p-4 sm:p-6 relative ${
                plan.popular ? 'border-gold-500/50 order-first sm:order-none' : 'border-premium-border'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg text-xs font-medium rounded-full whitespace-nowrap">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="mb-4 pt-1">
                <h3 className="text-base sm:text-lg font-semibold text-white">{plan.name}</h3>
                <div className="mt-2">
                  <span className="text-2xl sm:text-3xl font-bold text-white">${plan.price}</span>
                  <span className="text-gray-500 text-xs sm:text-sm">/{plan.period}</span>
                </div>
              </div>

              <ul className="space-y-2.5 sm:space-y-3 mb-5 sm:mb-6">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-start text-xs sm:text-sm">
                    <Check className="h-4 w-4 text-gold-400 mr-2 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => plan.id !== 'free' && handleUpgrade(plan.id)}
                disabled={plan.id === 'free' || isLoading === plan.id || (currentPlan === 'premium' && plan.id === 'premium')}
                className={`w-full py-3 sm:py-2.5 rounded-lg font-medium transition-all min-h-[48px] touch-manipulation text-sm sm:text-base ${
                  plan.popular
                    ? 'bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg hover:shadow-gold active:scale-98'
                    : plan.id === 'free'
                    ? 'bg-premium-surface text-gray-400 cursor-not-allowed'
                    : 'border border-premium-border text-white hover:bg-premium-surface active:bg-premium-surface/80'
                } ${isLoading === plan.id || (currentPlan === 'premium' && plan.id === 'premium') ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {isLoading === plan.id ? (
                  <span className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-current mr-2"></div>
                    Processing...
                  </span>
                ) : currentPlan === 'premium' && plan.id === 'premium' ? (
                  'Current Plan'
                ) : (
                  plan.cta
                )}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Payment Methods */}
      {status?.subscription.status === 'active' && (
        <CollapsibleSection title="Payment Methods" icon={CreditCard} defaultOpen={false}>
          {paymentMethods.length > 0 ? (
            <div className="space-y-3">
              {paymentMethods.map((method) => (
                <div key={method.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 sm:p-4 bg-premium-surface rounded-lg gap-3">
                  <div className="flex items-center">
                    <div className="w-10 h-7 bg-gradient-to-r from-blue-600 to-blue-400 rounded flex items-center justify-center mr-3 flex-shrink-0">
                      <span className="text-white text-xs font-bold uppercase">
                        {method.card_brand || 'CARD'}
                      </span>
                    </div>
                    <div>
                      <p className="text-white text-sm flex flex-wrap items-center gap-2">
                        <span>**** **** **** {method.card_last4}</span>
                        {method.is_default && (
                          <span className="px-2 py-0.5 bg-gold-500/20 text-gold-400 text-xs rounded">
                            Default
                          </span>
                        )}
                      </p>
                      <p className="text-gray-500 text-xs">
                        Expires {method.card_exp_month}/{method.card_exp_year}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleManageSubscription}
                    className="text-gold-400 text-sm hover:text-gold-300 transition-colors min-h-[44px] touch-manipulation self-end sm:self-center px-2"
                  >
                    Update
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-gray-400 text-sm">No payment methods on file</p>
              <button
                onClick={handleManageSubscription}
                className="mt-3 text-gold-400 text-sm hover:text-gold-300 min-h-[44px] touch-manipulation px-4"
              >
                Add Payment Method
              </button>
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* Invoice History */}
      {status?.subscription.status === 'active' && (
        <CollapsibleSection title="Invoice History" icon={FileText} defaultOpen={false}>
          <div className="flex justify-end mb-3 -mt-2">
            <button
              onClick={fetchBillingData}
              disabled={loadingInvoices}
              className="text-gray-400 hover:text-white transition-colors p-2 min-w-[44px] min-h-[44px] flex items-center justify-center touch-manipulation"
              aria-label="Refresh invoices"
            >
              <RefreshCw className={`h-4 w-4 ${loadingInvoices ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {invoices.length > 0 ? (
            <div className="space-y-2">
              {invoices.map((invoice) => (
                <div key={invoice.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-premium-surface rounded-lg gap-2 sm:gap-4">
                  <div className="flex items-center justify-between sm:justify-start flex-1">
                    <div className="mr-3">
                      <p className="text-white text-sm">{invoice.number || 'Invoice'}</p>
                      <p className="text-gray-500 text-xs">
                        {new Date(invoice.created).toLocaleDateString()}
                      </p>
                    </div>
                    <span className={`text-xs sm:hidden px-2 py-0.5 rounded ${
                      invoice.status === 'paid' ? 'bg-emerald-500/20 text-emerald-400' :
                      invoice.status === 'open' ? 'bg-gold-500/20 text-gold-400' : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between sm:justify-end gap-4">
                    <div className="text-left sm:text-right">
                      <p className="text-white text-sm font-medium">
                        {formatCurrency(invoice.amount_paid, invoice.currency)}
                      </p>
                      <span className={`text-xs hidden sm:inline ${
                        invoice.status === 'paid' ? 'text-emerald-400' :
                        invoice.status === 'open' ? 'text-gold-400' : 'text-gray-400'
                      }`}>
                        {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                      </span>
                    </div>
                    {invoice.invoice_pdf && (
                      <a
                        href={invoice.invoice_pdf}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gold-400 hover:text-gold-300 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center touch-manipulation"
                        aria-label="Download invoice PDF"
                      >
                        <Download className="h-5 w-5" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm text-center py-6">No invoices yet</p>
          )}

          {invoices.length > 0 && (
            <button
              onClick={handleManageSubscription}
              className="mt-4 w-full py-3 border border-premium-border text-gray-300 rounded-lg hover:bg-premium-surface transition-colors text-sm min-h-[48px] touch-manipulation"
            >
              View All Invoices
            </button>
          )}
        </CollapsibleSection>
      )}

      {/* FAQ */}
      <CollapsibleSection title="Frequently Asked Questions" defaultOpen={false}>
        <div className="space-y-4 sm:space-y-5">
          <div className="p-3 sm:p-0">
            <h4 className="text-white font-medium mb-1.5 text-sm sm:text-base">Can I cancel anytime?</h4>
            <p className="text-gray-400 text-xs sm:text-sm leading-relaxed">
              Yes, you can cancel your subscription at any time. You&apos;ll continue to have access until the end of your billing period.
            </p>
          </div>

          <div className="p-3 sm:p-0 border-t border-premium-border sm:border-0 pt-4 sm:pt-0">
            <h4 className="text-white font-medium mb-1.5 text-sm sm:text-base">What happens to my data if I downgrade?</h4>
            <p className="text-gray-400 text-xs sm:text-sm leading-relaxed">
              Your data is preserved. On the free plan, you&apos;ll only have access to your last 7 days of meetings.
            </p>
          </div>

          <div className="p-3 sm:p-0 border-t border-premium-border sm:border-0 pt-4 sm:pt-0">
            <h4 className="text-white font-medium mb-1.5 text-sm sm:text-base">Do you offer refunds?</h4>
            <p className="text-gray-400 text-xs sm:text-sm leading-relaxed">
              We offer a full refund within 14 days of your first subscription if you&apos;re not satisfied.
            </p>
          </div>
        </div>
      </CollapsibleSection>
    </div>
  )
}

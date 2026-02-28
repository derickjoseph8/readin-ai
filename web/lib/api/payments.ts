/**
 * Payments & Subscription API
 */

import apiClient from './client'

// =============================================================================
// TYPES
// =============================================================================

export interface SubscriptionStatus {
  status: string
  plan: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  trial_ends_at: string | null
}

export interface Invoice {
  id: string
  number: string | null
  amount_due: number
  amount_paid: number
  currency: string
  status: string
  created: string
  invoice_pdf: string | null
  hosted_invoice_url: string | null
}

export interface PaymentMethod {
  id: string
  type: string
  card_brand: string | null
  card_last4: string | null
  card_exp_month: number | null
  card_exp_year: number | null
  is_default: boolean
}

export interface PricingPlan {
  id: string
  name: string
  price: number
  currency: string
  interval: string | null
  features: string[]
}

export interface PricingInfo {
  plans: PricingPlan[]
}

// =============================================================================
// PAYMENTS API
// =============================================================================

export interface CheckoutOptions {
  plan?: 'individual' | 'starter' | 'team'
  seats?: number
  is_annual?: boolean
  success_url?: string
  cancel_url?: string
}

export const paymentsApi = {
  /**
   * Create a Paystack checkout session for subscription
   */
  async createCheckout(options: CheckoutOptions = {}): Promise<{ checkout_url: string; authorization_url?: string }> {
    const {
      plan = 'individual',
      seats = 1,
      is_annual = false,
      success_url,
      cancel_url,
    } = options

    // Use Paystack
    const response = await apiClient.post<{ authorization_url?: string; checkout_url?: string }>('/api/v1/payments/paystack/checkout', {
      plan,
      seats,
      is_annual,
      success_url: success_url || `${typeof window !== 'undefined' ? window.location.origin : ''}/dashboard/settings/billing?success=true`,
      cancel_url: cancel_url || `${typeof window !== 'undefined' ? window.location.origin : ''}/dashboard/settings/billing?cancelled=true`,
    })

    // Paystack returns authorization_url
    if (response.authorization_url) {
      return { checkout_url: response.authorization_url, ...response }
    }
    return { checkout_url: response.checkout_url || '', ...response }
  },

  /**
   * Get billing portal URL
   */
  async getBillingPortal(): Promise<{ portal_url: string }> {
    return apiClient.post('/api/v1/payments/portal')
  },

  /**
   * Get current subscription status
   */
  async getSubscriptionStatus(): Promise<SubscriptionStatus> {
    return apiClient.get('/api/v1/payments/subscription')
  },

  /**
   * Cancel subscription at period end
   */
  async cancelSubscription(): Promise<{ message: string; cancel_at: string }> {
    return apiClient.post('/api/v1/payments/subscription/cancel')
  },

  /**
   * Reactivate a cancelled subscription
   */
  async reactivateSubscription(): Promise<{ message: string; status: string }> {
    return apiClient.post('/api/v1/payments/subscription/reactivate')
  },

  /**
   * Get invoice history
   */
  async getInvoices(limit: number = 10): Promise<Invoice[]> {
    return apiClient.get(`/api/v1/payments/invoices?limit=${limit}`)
  },

  /**
   * Get a specific invoice
   */
  async getInvoice(invoiceId: string): Promise<Invoice> {
    return apiClient.get(`/api/v1/payments/invoices/${invoiceId}`)
  },

  /**
   * Get saved payment methods
   */
  async getPaymentMethods(): Promise<PaymentMethod[]> {
    return apiClient.get('/api/v1/payments/payment-methods')
  },

  /**
   * Set default payment method
   */
  async setDefaultPaymentMethod(methodId: string): Promise<{ message: string }> {
    return apiClient.post(`/api/v1/payments/payment-methods/${methodId}/default`)
  },

  /**
   * Delete a payment method
   */
  async deletePaymentMethod(methodId: string): Promise<{ message: string }> {
    return apiClient.delete(`/api/v1/payments/payment-methods/${methodId}`)
  },

  /**
   * Get pricing information
   */
  async getPricing(): Promise<PricingInfo> {
    return apiClient.get('/api/v1/payments/pricing')
  },
}

export default paymentsApi

import re

with open('/var/www/readin-ai/web/app/(static)/dashboard/settings/billing/page.tsx', 'r') as f:
    content = f.read()

# Add Script import
old_imports = "import { useState, useEffect } from 'react'"
new_imports = """import { useState, useEffect } from 'react'
import Script from 'next/script'"""

content = content.replace(old_imports, new_imports)

# Find and replace the handleUpgrade function using regex
old_handle_pattern = r"const handleUpgrade = async \(planId: string\) => \{[\s\S]*?finally \{\s*setIsLoading\(null\)\s*\}\s*\}"

new_handle = '''const handleUpgrade = async (planId: string) => {
    if (!canManageBilling) return
    setIsLoading(planId)

    try {
      // Map planId to checkout options
      const plan = planId === 'premium' ? 'individual' : planId === 'team' ? 'starter' : 'individual'
      const seats = plan === 'individual' ? 1 : 3

      // Get popup data from backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us'}/api/v1/payments/paystack/popup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ plan, seats, is_annual: false }),
      })

      const popupData = await response.json()

      if (!response.ok) {
        throw new Error(popupData.detail || 'Failed to initialize payment')
      }

      // Initialize Paystack popup
      const PaystackPop = (window as any).PaystackPop
      if (!PaystackPop) {
        throw new Error('Payment system not loaded. Please refresh the page.')
      }

      const handler = PaystackPop.setup({
        key: popupData.key,
        email: popupData.email,
        amount: popupData.amount,
        currency: popupData.currency,
        ref: popupData.ref,
        metadata: popupData.metadata,
        onClose: () => {
          setIsLoading(null)
        },
        callback: async (response: { reference: string }) => {
          // Verify payment on backend
          try {
            const verifyResponse = await fetch(
              `${process.env.NEXT_PUBLIC_API_URL || 'https://www.getreadin.us'}/api/v1/payments/paystack/verify/${response.reference}`,
              {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
              }
            )

            if (verifyResponse.ok) {
              alert('Payment successful! Your account has been upgraded.')
              window.location.reload()
            } else {
              alert('Payment verification failed. Please contact support.')
            }
          } catch (err) {
            console.error('Verification error:', err)
            alert('Payment verification failed. Please contact support.')
          } finally {
            setIsLoading(null)
          }
        },
      })

      handler.openIframe()
    } catch (error) {
      console.error('Upgrade failed:', error)
      alert(error instanceof Error ? error.message : 'Failed to create checkout session. Please try again.')
      setIsLoading(null)
    }
  }'''

content = re.sub(old_handle_pattern, new_handle, content)

# Add Paystack script - find return ( and wrap with fragment
content = content.replace(
    "  return (\n    <div className",
    """  return (
    <>
      <Script
        src="https://js.paystack.co/v1/inline.js"
        strategy="lazyOnload"
      />
      <div className"""
)

# Close the fragment - find the last </div> before the final ) and add </>
# Find pattern: </div>\n  )\n}
content = re.sub(
    r'(</div>\s*\n\s*)\)\s*\n\}$',
    r'\1    </>\n  )\n}',
    content
)

with open('/var/www/readin-ai/web/app/(static)/dashboard/settings/billing/page.tsx', 'w') as f:
    f.write(content)

print('Updated billing page with Paystack popup')

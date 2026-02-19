'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function SignupRedirect() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/login?mode=signup')
  }, [router])

  return (
    <main className="min-h-screen bg-premium-bg flex items-center justify-center">
      <div className="text-white">Redirecting to sign up...</div>
    </main>
  )
}

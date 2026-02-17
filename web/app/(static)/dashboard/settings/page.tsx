'use client'

import { useState, useEffect } from 'react'
import { User, Mail, Briefcase, Save, Check } from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import { authApi } from '@/lib/api/auth'

export default function SettingsPage() {
  const { user, refreshStatus } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    profession: '',
    company: '',
  })

  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || '',
        email: user.email || '',
        profession: user.profession_name || '',
        company: user.company_name || '',
      })
    }
  }, [user])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
    setIsSaved(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      await authApi.updateProfile({
        full_name: formData.full_name,
        profession: formData.profession,
        company: formData.company,
      })
      await refreshStatus()
      setIsSaved(true)
      setTimeout(() => setIsSaved(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update profile')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Profile Settings</h1>
        <p className="text-gray-400 mt-1">
          Manage your account information
        </p>
      </div>

      {/* Profile Form */}
      <form onSubmit={handleSubmit} className="bg-premium-card border border-premium-border rounded-xl p-6 space-y-6">
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {isSaved && (
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-sm flex items-center">
            <Check className="h-4 w-4 mr-2" />
            Profile updated successfully
          </div>
        )}

        {/* Avatar */}
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-gold-500/20 rounded-full flex items-center justify-center">
            <span className="text-gold-400 text-2xl font-bold">
              {formData.full_name?.[0] || formData.email?.[0] || 'U'}
            </span>
          </div>
          <div>
            <p className="text-white font-medium">{formData.full_name || 'User'}</p>
            <p className="text-gray-500 text-sm">{formData.email}</p>
          </div>
        </div>

        {/* Full Name */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Full Name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <input
              type="text"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              className="w-full pl-10 pr-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
              placeholder="Enter your full name"
            />
          </div>
        </div>

        {/* Email (read-only) */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Email Address
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <input
              type="email"
              name="email"
              value={formData.email}
              disabled
              className="w-full pl-10 pr-4 py-2.5 bg-premium-surface/50 border border-premium-border rounded-lg text-gray-400 cursor-not-allowed"
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
        </div>

        {/* Profession */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Profession
          </label>
          <div className="relative">
            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <select
              name="profession"
              value={formData.profession}
              onChange={handleChange}
              className="w-full pl-10 pr-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white focus:outline-none focus:border-gold-500/50 appearance-none"
            >
              <option value="">Select your profession</option>
              <option value="software_engineer">Software Engineer</option>
              <option value="product_manager">Product Manager</option>
              <option value="designer">Designer</option>
              <option value="sales">Sales</option>
              <option value="marketing">Marketing</option>
              <option value="consultant">Consultant</option>
              <option value="executive">Executive</option>
              <option value="student">Student</option>
              <option value="other">Other</option>
            </select>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Helps ReadIn AI provide more relevant responses
          </p>
        </div>

        {/* Company */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Company (Optional)
          </label>
          <input
            type="text"
            name="company"
            value={formData.company}
            onChange={handleChange}
            className="w-full px-4 py-2.5 bg-premium-surface border border-premium-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500/50"
            placeholder="Enter your company name"
          />
        </div>

        {/* Submit Button */}
        <div className="pt-4">
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-2.5 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all disabled:opacity-50 flex items-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-premium-bg mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </form>

      {/* Danger Zone */}
      <div className="bg-premium-card border border-red-500/30 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-2">Danger Zone</h3>
        <p className="text-gray-400 text-sm mb-4">
          Once you delete your account, there is no going back. Please be certain.
        </p>
        <button
          className="px-4 py-2 border border-red-500/50 text-red-400 rounded-lg hover:bg-red-500/10 transition-colors text-sm"
          onClick={() => {
            if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
              // Handle account deletion
              alert('Please contact support to delete your account.')
            }
          }}
        >
          Delete Account
        </button>
      </div>
    </div>
  )
}

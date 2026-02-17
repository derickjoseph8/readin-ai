'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  X,
  Download,
  Calendar,
  Mic,
  MessageSquare,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Shield,
  Zap,
  Settings,
  HelpCircle
} from 'lucide-react'

interface OnboardingProps {
  userName?: string
  onComplete: () => void
  onSkip: () => void
}

interface OnboardingStep {
  id: string
  title: string
  description: string
  icon: React.ElementType
  action?: {
    label: string
    href?: string
    onClick?: () => void
  }
  tip?: string
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to ReadIn AI',
    description: 'Your AI-powered meeting assistant that provides real-time talking points and summaries. Let\'s get you set up in just a few steps.',
    icon: Sparkles,
    tip: 'This setup takes about 2 minutes'
  },
  {
    id: 'download',
    title: 'Download the Desktop App',
    description: 'ReadIn AI works best with our desktop application. It runs quietly in the background and activates automatically when you join meetings.',
    icon: Download,
    action: {
      label: 'Download for Your OS',
      href: '/download'
    },
    tip: 'Available for Windows, macOS, and Linux'
  },
  {
    id: 'audio',
    title: 'Audio Setup',
    description: 'The desktop app will guide you through selecting your microphone and audio settings. Make sure to grant microphone permissions when prompted.',
    icon: Mic,
    tip: 'Works with any microphone including built-in ones'
  },
  {
    id: 'calendar',
    title: 'Connect Your Calendar',
    description: 'Link your Google or Microsoft calendar to get automatic meeting preparation and briefings before each meeting.',
    icon: Calendar,
    action: {
      label: 'Connect Calendar',
      href: '/dashboard/settings/calendar'
    },
    tip: 'Optional but highly recommended'
  },
  {
    id: 'ready',
    title: 'You\'re All Set!',
    description: 'Start any meeting and ReadIn AI will automatically detect it and provide real-time assistance. Check the tips below to get the most out of your experience.',
    icon: CheckCircle,
    tip: 'Press Ctrl+Shift+R to toggle the overlay anytime'
  }
]

export default function Onboarding({ userName, onComplete, onSkip }: OnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())

  const step = ONBOARDING_STEPS[currentStep]
  const isFirstStep = currentStep === 0
  const isLastStep = currentStep === ONBOARDING_STEPS.length - 1
  const progress = ((currentStep + 1) / ONBOARDING_STEPS.length) * 100

  const handleNext = () => {
    setCompletedSteps(prev => {
      const newSet = new Set(prev)
      newSet.add(step.id)
      return newSet
    })
    if (isLastStep) {
      onComplete()
    } else {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handlePrevious = () => {
    if (!isFirstStep) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleStepClick = (index: number) => {
    if (index <= currentStep || completedSteps.has(ONBOARDING_STEPS[index - 1]?.id)) {
      setCurrentStep(index)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
    >
      <div className="w-full max-w-2xl mx-4 bg-premium-card border border-premium-border rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-premium-border">
          <div className="flex items-center space-x-2">
            <Sparkles className="h-5 w-5 text-gold-400" aria-hidden="true" />
            <span className="text-white font-medium">Getting Started</span>
          </div>
          <button
            onClick={onSkip}
            className="text-gray-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-premium-surface focus:outline-none focus:ring-2 focus:ring-gold-500"
            aria-label="Skip onboarding"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="px-6 pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Step {currentStep + 1} of {ONBOARDING_STEPS.length}</span>
            <span className="text-sm text-gold-400">{Math.round(progress)}% complete</span>
          </div>
          <div
            className="h-1 bg-premium-surface rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Onboarding progress"
          >
            <div
              className="h-full bg-gradient-to-r from-gold-600 to-gold-400 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Step Indicators */}
          <div className="flex justify-between mt-4" role="tablist" aria-label="Onboarding steps">
            {ONBOARDING_STEPS.map((s, index) => (
              <button
                key={s.id}
                onClick={() => handleStepClick(index)}
                disabled={index > currentStep && !completedSteps.has(ONBOARDING_STEPS[index - 1]?.id)}
                className={`flex flex-col items-center group focus:outline-none focus:ring-2 focus:ring-gold-500 rounded-lg p-1 ${
                  index <= currentStep ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
                }`}
                role="tab"
                aria-selected={index === currentStep}
                aria-label={`Step ${index + 1}: ${s.title}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                  index < currentStep
                    ? 'bg-emerald-500 text-white'
                    : index === currentStep
                      ? 'bg-gold-500 text-premium-bg'
                      : 'bg-premium-surface text-gray-500'
                }`}>
                  {index < currentStep ? (
                    <CheckCircle className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <s.icon className="h-4 w-4" aria-hidden="true" />
                  )}
                </div>
                <span className={`text-xs mt-1 hidden sm:block ${
                  index === currentStep ? 'text-gold-400' : 'text-gray-500'
                }`}>
                  {s.title.split(' ')[0]}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gold-500/20 flex items-center justify-center">
              <step.icon className="h-8 w-8 text-gold-400" aria-hidden="true" />
            </div>
            <h2 id="onboarding-title" className="text-2xl font-bold text-white">
              {isFirstStep && userName ? `Welcome, ${userName}!` : step.title}
            </h2>
            <p className="text-gray-400 mt-3 max-w-md mx-auto">
              {step.description}
            </p>
          </div>

          {/* Action Button */}
          {step.action && (
            <div className="flex justify-center">
              {step.action.href ? (
                <Link
                  href={step.action.href}
                  className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all focus:outline-none focus:ring-2 focus:ring-gold-500 focus:ring-offset-2 focus:ring-offset-premium-bg"
                >
                  {step.action.label}
                  <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
                </Link>
              ) : (
                <button
                  onClick={step.action.onClick}
                  className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all focus:outline-none focus:ring-2 focus:ring-gold-500 focus:ring-offset-2 focus:ring-offset-premium-bg"
                >
                  {step.action.label}
                  <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
                </button>
              )}
            </div>
          )}

          {/* Tip */}
          {step.tip && (
            <div className="flex items-start space-x-3 p-4 bg-premium-surface rounded-lg border border-premium-border">
              <Zap className="h-5 w-5 text-gold-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <p className="text-sm text-gray-300">{step.tip}</p>
            </div>
          )}

          {/* Final Step - Quick Tips */}
          {isLastStep && (
            <div className="grid sm:grid-cols-3 gap-4 mt-6">
              <div className="p-4 bg-premium-surface rounded-lg text-center">
                <Shield className="h-6 w-6 text-emerald-400 mx-auto mb-2" aria-hidden="true" />
                <h4 className="text-white text-sm font-medium">Privacy First</h4>
                <p className="text-gray-500 text-xs mt-1">Audio is processed locally</p>
              </div>
              <div className="p-4 bg-premium-surface rounded-lg text-center">
                <Settings className="h-6 w-6 text-blue-400 mx-auto mb-2" aria-hidden="true" />
                <h4 className="text-white text-sm font-medium">Customize</h4>
                <p className="text-gray-500 text-xs mt-1">Adjust in Settings</p>
              </div>
              <div className="p-4 bg-premium-surface rounded-lg text-center">
                <HelpCircle className="h-6 w-6 text-purple-400 mx-auto mb-2" aria-hidden="true" />
                <h4 className="text-white text-sm font-medium">Need Help?</h4>
                <p className="text-gray-500 text-xs mt-1">Visit our support page</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-premium-border bg-premium-surface/50">
          <button
            onClick={handlePrevious}
            disabled={isFirstStep}
            className={`flex items-center px-4 py-2 text-sm rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gold-500 ${
              isFirstStep
                ? 'text-gray-600 cursor-not-allowed'
                : 'text-gray-400 hover:text-white hover:bg-premium-surface'
            }`}
            aria-label="Go to previous step"
          >
            <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
            Back
          </button>

          <div className="flex items-center space-x-3">
            <button
              onClick={onSkip}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-gold-500 rounded-lg"
            >
              Skip for now
            </button>
            <button
              onClick={handleNext}
              className="flex items-center px-6 py-2 bg-gold-500 text-premium-bg font-medium text-sm rounded-lg hover:bg-gold-400 transition-colors focus:outline-none focus:ring-2 focus:ring-gold-500 focus:ring-offset-2 focus:ring-offset-premium-bg"
            >
              {isLastStep ? 'Get Started' : 'Continue'}
              <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

'use client'

import { useState, useRef } from 'react'
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
  HelpCircle,
  User,
  BookOpen,
  PlayCircle,
  Info,
  Lightbulb
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
  tooltips?: { text: string; position: 'top' | 'bottom' | 'left' | 'right' }[]
  content?: React.ReactNode
}

// Profession/role options for the setup step
const PROFESSION_OPTIONS = [
  { id: 'sales', label: 'Sales / Business Development', icon: '💼' },
  { id: 'engineering', label: 'Engineering / Technical', icon: '⚙️' },
  { id: 'product', label: 'Product Management', icon: '📊' },
  { id: 'design', label: 'Design / Creative', icon: '🎨' },
  { id: 'marketing', label: 'Marketing / Communications', icon: '📣' },
  { id: 'hr', label: 'Human Resources', icon: '👥' },
  { id: 'finance', label: 'Finance / Accounting', icon: '💰' },
  { id: 'legal', label: 'Legal / Compliance', icon: '⚖️' },
  { id: 'executive', label: 'Executive / Leadership', icon: '🎯' },
  { id: 'other', label: 'Other', icon: '✨' }
]

// Tooltip component
function Tooltip({
  children,
  text,
  position = 'top'
}: {
  children: React.ReactNode
  text: string
  position?: 'top' | 'bottom' | 'left' | 'right'
}) {
  const [isVisible, setIsVisible] = useState(false)

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2'
  }

  const arrowClasses = {
    top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800 border-x-transparent border-b-transparent',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800 border-x-transparent border-t-transparent',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800 border-y-transparent border-r-transparent',
    right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800 border-y-transparent border-l-transparent'
  }

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div
          className={`absolute z-50 px-3 py-2 text-xs text-white bg-gray-800 rounded-lg shadow-lg whitespace-nowrap ${positionClasses[position]} animate-fadeIn`}
          role="tooltip"
        >
          {text}
          <div className={`absolute w-0 h-0 border-4 ${arrowClasses[position]}`} />
        </div>
      )}
    </div>
  )
}

// Feature highlight component with tooltip
function FeatureHighlight({
  icon: Icon,
  title,
  description,
  tooltipText
}: {
  icon: React.ElementType
  title: string
  description: string
  tooltipText: string
}) {
  return (
    <Tooltip text={tooltipText} position="top">
      <div className="p-4 bg-premium-surface rounded-lg border border-premium-border hover:border-gold-500/50 transition-all cursor-help group">
        <div className="flex items-start space-x-3">
          <div className="w-10 h-10 rounded-lg bg-gold-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-gold-500/30 transition-colors">
            <Icon className="h-5 w-5 text-gold-400" />
          </div>
          <div>
            <h4 className="text-white text-sm font-medium flex items-center">
              {title}
              <Info className="h-3 w-3 ml-1 text-gray-500" />
            </h4>
            <p className="text-gray-500 text-xs mt-1">{description}</p>
          </div>
        </div>
      </div>
    </Tooltip>
  )
}

export default function Onboarding({ userName, onComplete, onSkip }: OnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())
  const [selectedProfession, setSelectedProfession] = useState<string | null>(null)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [slideDirection, setSlideDirection] = useState<'left' | 'right'>('right')
  const contentRef = useRef<HTMLDivElement>(null)

  // Step definitions
  const ONBOARDING_STEPS: OnboardingStep[] = [
    {
      id: 'welcome',
      title: 'Welcome to ReadIn AI',
      description: 'Your AI-powered meeting assistant that provides real-time talking points and summaries. Let\'s get you set up in just a few steps.',
      icon: Sparkles,
      tip: 'This setup takes about 2 minutes'
    },
    {
      id: 'profession',
      title: 'Tell Us About Yourself',
      description: 'Select your profession or role so we can personalize your ReadIn AI experience with relevant talking points and insights.',
      icon: User,
      tip: 'This helps us tailor meeting suggestions to your needs'
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
      id: 'calendar',
      title: 'Connect Your Calendar',
      description: 'Link your Google or Microsoft calendar to get automatic meeting preparation and briefings before each meeting.',
      icon: Calendar,
      action: {
        label: 'Connect Calendar',
        href: '/dashboard/settings/calendar'
      },
      tip: 'Optional but highly recommended for the best experience'
    },
    {
      id: 'tips',
      title: 'Quick Tips',
      description: 'Here are some helpful tips to get the most out of ReadIn AI. Hover over each feature to learn more.',
      icon: Lightbulb,
      tip: 'You can always access these tips from the Help menu'
    },
    {
      id: 'ready',
      title: 'You\'re All Set!',
      description: 'Start any meeting and ReadIn AI will automatically detect it and provide real-time assistance.',
      icon: CheckCircle,
      tip: 'Press Ctrl+Shift+R to toggle the overlay anytime'
    }
  ]

  const step = ONBOARDING_STEPS[currentStep]
  const isFirstStep = currentStep === 0
  const isLastStep = currentStep === ONBOARDING_STEPS.length - 1
  const totalSteps = ONBOARDING_STEPS.length
  const progress = ((currentStep + 1) / totalSteps) * 100

  // Handle step transitions with animation
  const transitionToStep = (newStep: number, direction: 'left' | 'right') => {
    setIsTransitioning(true)
    setSlideDirection(direction)

    setTimeout(() => {
      setCurrentStep(newStep)
      setIsTransitioning(false)
    }, 200)
  }

  const handleNext = () => {
    setCompletedSteps(prev => {
      const newSet = new Set(prev)
      newSet.add(step.id)
      return newSet
    })

    if (isLastStep) {
      onComplete()
    } else {
      transitionToStep(currentStep + 1, 'right')
    }
  }

  const handlePrevious = () => {
    if (!isFirstStep) {
      transitionToStep(currentStep - 1, 'left')
    }
  }

  const handleStepClick = (index: number) => {
    if (index <= currentStep || completedSteps.has(ONBOARDING_STEPS[index - 1]?.id)) {
      const direction = index > currentStep ? 'right' : 'left'
      transitionToStep(index, direction)
    }
  }

  const canProceed = () => {
    if (step.id === 'profession') {
      return selectedProfession !== null
    }
    return true
  }

  // Render profession selection grid
  const renderProfessionStep = () => (
    <div className="grid grid-cols-2 gap-3 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
      {PROFESSION_OPTIONS.map((profession) => (
        <button
          key={profession.id}
          onClick={() => setSelectedProfession(profession.id)}
          className={`p-3 rounded-lg border text-left transition-all ${
            selectedProfession === profession.id
              ? 'border-gold-500 bg-gold-500/20 ring-2 ring-gold-500/50'
              : 'border-premium-border bg-premium-surface hover:border-gray-600 hover:bg-premium-surface/80'
          }`}
        >
          <span className="text-xl mr-2">{profession.icon}</span>
          <span className={`text-sm ${selectedProfession === profession.id ? 'text-gold-400' : 'text-gray-300'}`}>
            {profession.label}
          </span>
        </button>
      ))}
    </div>
  )

  // Render quick tips step with tooltips
  const renderTipsStep = () => (
    <div className="space-y-3">
      <FeatureHighlight
        icon={Mic}
        title="Real-time Transcription"
        description="Automatic speech-to-text during meetings"
        tooltipText="ReadIn AI transcribes your meetings in real-time, allowing you to focus on the conversation instead of taking notes."
      />
      <FeatureHighlight
        icon={MessageSquare}
        title="AI Talking Points"
        description="Get suggested responses and insights"
        tooltipText="Our AI analyzes the conversation and suggests relevant talking points, statistics, and responses you can use."
      />
      <FeatureHighlight
        icon={Calendar}
        title="Pre-meeting Briefs"
        description="Automatic preparation for upcoming meetings"
        tooltipText="Before each meeting, ReadIn AI prepares a brief with attendee information, past interactions, and relevant context."
      />
      <FeatureHighlight
        icon={Shield}
        title="Privacy First"
        description="Your audio is processed locally"
        tooltipText="All audio processing happens on your device. We never store or transmit your meeting audio to external servers."
      />
    </div>
  )

  // Render final step with summary
  const renderFinalStep = () => (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-3 gap-4">
        <div className="p-4 bg-premium-surface rounded-lg text-center border border-premium-border">
          <Shield className="h-6 w-6 text-emerald-400 mx-auto mb-2" aria-hidden="true" />
          <h4 className="text-white text-sm font-medium">Privacy First</h4>
          <p className="text-gray-500 text-xs mt-1">Audio is processed locally</p>
        </div>
        <div className="p-4 bg-premium-surface rounded-lg text-center border border-premium-border">
          <Settings className="h-6 w-6 text-blue-400 mx-auto mb-2" aria-hidden="true" />
          <h4 className="text-white text-sm font-medium">Customize</h4>
          <p className="text-gray-500 text-xs mt-1">Adjust in Settings</p>
        </div>
        <div className="p-4 bg-premium-surface rounded-lg text-center border border-premium-border">
          <HelpCircle className="h-6 w-6 text-purple-400 mx-auto mb-2" aria-hidden="true" />
          <h4 className="text-white text-sm font-medium">Need Help?</h4>
          <p className="text-gray-500 text-xs mt-1">Visit our support page</p>
        </div>
      </div>

      {/* Watch Tutorial Button */}
      <div className="flex justify-center pt-2">
        <Link
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center px-4 py-2 text-sm text-gold-400 border border-gold-500/50 rounded-lg hover:bg-gold-500/10 transition-all"
        >
          <PlayCircle className="h-4 w-4 mr-2" />
          Watch Tutorial
        </Link>
      </div>
    </div>
  )

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
          <div className="flex items-center space-x-3">
            {/* Watch Tutorial Link in Header */}
            <Tooltip text="View documentation and tutorials" position="bottom">
              <Link
                href="/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-sm text-gray-400 hover:text-gold-400 transition-colors"
              >
                <BookOpen className="h-4 w-4 mr-1" />
                <span className="hidden sm:inline">Docs</span>
              </Link>
            </Tooltip>
            <button
              onClick={onSkip}
              className="text-gray-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-premium-surface focus:outline-none focus:ring-2 focus:ring-gold-500"
              aria-label="Skip onboarding"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Enhanced Progress Bar */}
        <div className="px-6 pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400 font-medium">
              Step {currentStep + 1} of {totalSteps}
            </span>
            <span className="text-sm text-gold-400 font-medium">{Math.round(progress)}% complete</span>
          </div>

          {/* Animated Progress Bar */}
          <div
            className="h-2 bg-premium-surface rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Onboarding progress"
          >
            <div
              className="h-full bg-gradient-to-r from-gold-600 via-gold-500 to-gold-400 transition-all duration-500 ease-out relative overflow-hidden"
              style={{ width: `${progress}%` }}
            >
              {/* Shimmer effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
            </div>
          </div>

          {/* Step Indicators */}
          <div className="flex justify-between mt-4 relative" role="tablist" aria-label="Onboarding steps">
            {/* Connection Line */}
            <div className="absolute top-4 left-0 right-0 h-0.5 bg-premium-surface -z-10" />
            <div
              className="absolute top-4 left-0 h-0.5 bg-gold-500 transition-all duration-500 -z-10"
              style={{ width: `${(currentStep / (totalSteps - 1)) * 100}%` }}
            />

            {ONBOARDING_STEPS.map((s, index) => (
              <Tooltip key={s.id} text={s.title} position="bottom">
                <button
                  onClick={() => handleStepClick(index)}
                  disabled={index > currentStep && !completedSteps.has(ONBOARDING_STEPS[index - 1]?.id)}
                  className={`flex flex-col items-center group focus:outline-none focus:ring-2 focus:ring-gold-500 rounded-lg p-1 transition-all duration-300 ${
                    index <= currentStep ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
                  }`}
                  role="tab"
                  aria-selected={index === currentStep}
                  aria-label={`Step ${index + 1}: ${s.title}`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${
                    index < currentStep
                      ? 'bg-emerald-500 text-white scale-90'
                      : index === currentStep
                        ? 'bg-gold-500 text-premium-bg scale-110 ring-4 ring-gold-500/30'
                        : 'bg-premium-surface text-gray-500'
                  }`}>
                    {index < currentStep ? (
                      <CheckCircle className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <span className="text-xs font-bold">{index + 1}</span>
                    )}
                  </div>
                </button>
              </Tooltip>
            ))}
          </div>
        </div>

        {/* Content with Transitions */}
        <div
          ref={contentRef}
          className={`p-6 space-y-6 transition-all duration-200 ${
            isTransitioning
              ? slideDirection === 'right'
                ? 'opacity-0 translate-x-4'
                : 'opacity-0 -translate-x-4'
              : 'opacity-100 translate-x-0'
          }`}
        >
          <div className="text-center">
            <div className={`w-16 h-16 mx-auto mb-4 rounded-2xl bg-gold-500/20 flex items-center justify-center transition-transform duration-300 ${
              !isTransitioning ? 'scale-100' : 'scale-90'
            }`}>
              <step.icon className="h-8 w-8 text-gold-400" aria-hidden="true" />
            </div>
            <h2 id="onboarding-title" className="text-2xl font-bold text-white">
              {isFirstStep && userName ? `Welcome, ${userName}!` : step.title}
            </h2>
            <p className="text-gray-400 mt-3 max-w-md mx-auto">
              {step.description}
            </p>
          </div>

          {/* Step-specific Content */}
          {step.id === 'profession' && renderProfessionStep()}
          {step.id === 'tips' && renderTipsStep()}
          {step.id === 'ready' && renderFinalStep()}

          {/* Action Button */}
          {step.action && (
            <div className="flex justify-center">
              {step.action.href ? (
                <Link
                  href={step.action.href}
                  className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all hover:scale-105 focus:outline-none focus:ring-2 focus:ring-gold-500 focus:ring-offset-2 focus:ring-offset-premium-bg"
                >
                  {step.action.label}
                  <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
                </Link>
              ) : (
                <button
                  onClick={step.action.onClick}
                  className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-premium-bg font-medium rounded-lg hover:shadow-gold transition-all hover:scale-105 focus:outline-none focus:ring-2 focus:ring-gold-500 focus:ring-offset-2 focus:ring-offset-premium-bg"
                >
                  {step.action.label}
                  <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
                </button>
              )}
            </div>
          )}

          {/* Tip */}
          {step.tip && step.id !== 'ready' && step.id !== 'tips' && (
            <div className="flex items-start space-x-3 p-4 bg-premium-surface rounded-lg border border-premium-border">
              <Zap className="h-5 w-5 text-gold-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <p className="text-sm text-gray-300">{step.tip}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 border-t border-premium-border bg-premium-surface/50">
          <button
            onClick={handlePrevious}
            disabled={isFirstStep}
            className={`flex items-center px-4 py-2 text-sm rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-gold-500 order-2 sm:order-1 ${
              isFirstStep
                ? 'text-gray-600 cursor-not-allowed'
                : 'text-gray-400 hover:text-white hover:bg-premium-surface'
            }`}
            aria-label="Go to previous step"
          >
            <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
            Back
          </button>

          <div className="flex items-center space-x-3 order-1 sm:order-2 w-full sm:w-auto justify-center sm:justify-end">
            <button
              onClick={onSkip}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-gold-500 rounded-lg"
            >
              Skip for now
            </button>
            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className={`flex items-center px-6 py-2 font-medium text-sm rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-gold-500 focus:ring-offset-2 focus:ring-offset-premium-bg ${
                canProceed()
                  ? 'bg-gold-500 text-premium-bg hover:bg-gold-400 hover:scale-105'
                  : 'bg-gray-600 text-gray-400 cursor-not-allowed'
              }`}
            >
              {isLastStep ? 'Get Started' : 'Continue'}
              <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      {/* Custom Styles */}
      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }

        .animate-shimmer {
          animation: shimmer 2s infinite;
        }

        .animate-fadeIn {
          animation: fadeIn 0.15s ease-out;
        }

        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }

        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 3px;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </div>
  )
}

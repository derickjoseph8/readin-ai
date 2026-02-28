'use client';

import { useMemo } from 'react';
import { Check, X } from 'lucide-react';

interface PasswordStrengthProps {
  password: string;
  minLength?: number;
  showRequirements?: boolean;
}

interface PasswordRequirement {
  label: string;
  regex: RegExp;
  met: boolean;
}

/**
 * Password strength indicator with visual feedback.
 *
 * Shows:
 * - Strength bar (weak/fair/good/strong)
 * - Individual requirement status
 *
 * Usage:
 * ```tsx
 * <PasswordStrength password={password} showRequirements />
 * ```
 */
export default function PasswordStrength({
  password,
  minLength = 8,
  showRequirements = true
}: PasswordStrengthProps) {
  const requirements: PasswordRequirement[] = useMemo(() => [
    {
      label: `At least ${minLength} characters`,
      regex: new RegExp(`^.{${minLength},}$`),
      met: password.length >= minLength
    },
    {
      label: 'One uppercase letter',
      regex: /[A-Z]/,
      met: /[A-Z]/.test(password)
    },
    {
      label: 'One lowercase letter',
      regex: /[a-z]/,
      met: /[a-z]/.test(password)
    },
    {
      label: 'One number',
      regex: /\d/,
      met: /\d/.test(password)
    },
    {
      label: 'One special character',
      regex: /[!@#$%^&*(),.?":{}|<>]/,
      met: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    }
  ], [password, minLength]);

  const metCount = requirements.filter(r => r.met).length;

  const strength = useMemo(() => {
    if (!password) return { level: 0, label: '', color: 'bg-gray-700' };

    const score = metCount;

    if (score <= 1) return { level: 1, label: 'Weak', color: 'bg-red-500' };
    if (score <= 2) return { level: 2, label: 'Fair', color: 'bg-orange-500' };
    if (score <= 3) return { level: 3, label: 'Good', color: 'bg-yellow-500' };
    if (score <= 4) return { level: 4, label: 'Strong', color: 'bg-emerald-500' };
    return { level: 5, label: 'Very Strong', color: 'bg-green-500' };
  }, [password, metCount]);

  if (!password) return null;

  return (
    <div className="mt-2 space-y-3" role="status" aria-live="polite">
      {/* Strength Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-gray-400">Password strength</span>
          <span className={`font-medium ${
            strength.level <= 1 ? 'text-red-400' :
            strength.level <= 2 ? 'text-orange-400' :
            strength.level <= 3 ? 'text-yellow-400' :
            'text-emerald-400'
          }`}>
            {strength.label}
          </span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${strength.color}`}
            style={{ width: `${(strength.level / 5) * 100}%` }}
            role="progressbar"
            aria-valuenow={strength.level}
            aria-valuemin={0}
            aria-valuemax={5}
            aria-label={`Password strength: ${strength.label}`}
          />
        </div>
      </div>

      {/* Requirements List */}
      {showRequirements && (
        <ul className="space-y-1.5" aria-label="Password requirements">
          {requirements.map((req, index) => (
            <li
              key={index}
              className={`flex items-center gap-2 text-xs ${
                req.met ? 'text-emerald-400' : 'text-gray-500'
              }`}
            >
              {req.met ? (
                <Check className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
              ) : (
                <X className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
              )}
              <span>{req.label}</span>
              <span className="sr-only">{req.met ? '(met)' : '(not met)'}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Hook to check password strength programmatically.
 */
export function usePasswordStrength(password: string, minLength = 8) {
  return useMemo(() => {
    const checks = {
      length: password.length >= minLength,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };

    const score = Object.values(checks).filter(Boolean).length;
    const isValid = Object.values(checks).every(Boolean);

    return {
      checks,
      score,
      isValid,
      strength: score <= 1 ? 'weak' :
                score <= 2 ? 'fair' :
                score <= 3 ? 'good' :
                score <= 4 ? 'strong' : 'very-strong'
    };
  }, [password, minLength]);
}

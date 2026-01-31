'use client'

import { useEffect, useState } from 'react'

const stats = [
  { value: 2, suffix: 's', label: 'Average response time' },
  { value: 30, suffix: '+', label: 'Apps supported' },
  { value: 100, suffix: '%', label: 'Private & local audio' },
  { value: 10, suffix: 'k+', label: 'Active users' },
]

function AnimatedNumber({ value, suffix }: { value: number; suffix: string }) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    const duration = 2000
    const steps = 60
    const increment = value / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setCount(value)
        clearInterval(timer)
      } else {
        setCount(Math.floor(current))
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [value])

  return (
    <span className="text-5xl md:text-6xl font-bold text-gradient-gold">
      {count}{suffix}
    </span>
  )
}

export default function Stats() {
  return (
    <section className="py-20 px-4 bg-premium-surface/50">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {stats.map((stat, index) => (
            <div key={index} className="text-center">
              <AnimatedNumber value={stat.value} suffix={stat.suffix} />
              <p className="text-gray-400 mt-2">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

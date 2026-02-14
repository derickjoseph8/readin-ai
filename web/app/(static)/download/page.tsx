'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Download, Apple, Monitor, ArrowLeft, Check, X } from 'lucide-react'

export default function DownloadPage() {
  const [platform, setPlatform] = useState<'windows' | 'mac' | 'linux' | null>(null)
  const [downloadMessage, setDownloadMessage] = useState<{ os: string; show: boolean } | null>(null)

  useEffect(() => {
    // Detect platform
    const userAgent = navigator.userAgent.toLowerCase()
    if (userAgent.includes('win')) {
      setPlatform('windows')
    } else if (userAgent.includes('mac')) {
      setPlatform('mac')
    } else if (userAgent.includes('linux')) {
      setPlatform('linux')
    }
  }, [])

  const downloadUrls: Record<string, string> = {
    windows: 'https://www.getreadin.us/downloads/ReadInAI-Windows-1.0.1.zip',
    mac: 'https://www.getreadin.us/downloads/ReadInAI-macOS-1.0.1.dmg',
    linux: 'https://www.getreadin.us/downloads/ReadInAI-Linux-1.0.1.AppImage',
  }

  const handleDownloadClick = (os: string) => {
    setDownloadMessage({ os, show: true })
    setTimeout(() => {
      setDownloadMessage(null)
    }, 5000)
  }

  return (
    <main className="min-h-screen bg-dark-950 text-white">
      {/* Download Notification Toast */}
      {downloadMessage?.show && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl shadow-2xl shadow-green-900/30 px-6 py-4 flex items-center gap-4 border border-green-500/30">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <Download className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-semibold text-white">
                Download started for {downloadMessage.os.charAt(0).toUpperCase() + downloadMessage.os.slice(1)}
              </p>
              <p className="text-green-100 text-sm">
                Your download should begin automatically. Check your downloads folder.
              </p>
            </div>
            <button
              onClick={() => setDownloadMessage(null)}
              className="ml-2 p-1 hover:bg-white/20 rounded-full transition"
            >
              <X className="h-4 w-4 text-white" />
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-dark-950/80 backdrop-blur-lg border-b border-white/10">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">R</span>
              </div>
              <span className="text-xl font-bold text-white">ReadIn AI</span>
            </Link>
            <Link
              href="/"
              className="flex items-center text-gray-300 hover:text-white transition"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Home
            </Link>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            Download{' '}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400">
              ReadIn AI
            </span>
          </h1>
          <p className="text-xl text-gray-400 mb-12">
            Get started with your 7-day free trial. No credit card required.
          </p>

          {/* Download Cards */}
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {/* Windows */}
            <div
              className={`p-6 rounded-2xl border transition-all ${
                platform === 'windows'
                  ? 'bg-blue-600/20 border-blue-500/50'
                  : 'bg-dark-900/50 border-white/10 hover:border-white/20'
              }`}
            >
              <Monitor className="h-12 w-12 mx-auto mb-4 text-blue-400" />
              <h3 className="text-xl font-semibold mb-2">Windows</h3>
              <p className="text-gray-400 text-sm mb-4">Windows 10 or later</p>
              <a
                href={downloadUrls.windows}
                onClick={() => handleDownloadClick('windows')}
                className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-500 rounded-lg font-medium hover:opacity-90 transition flex items-center justify-center"
              >
                <Download className="h-5 w-5 mr-2" />
                Download .zip
              </a>
              {platform === 'windows' && (
                <p className="text-green-400 text-xs mt-2 flex items-center justify-center">
                  <Check className="h-3 w-3 mr-1" /> Recommended for your system
                </p>
              )}
            </div>

            {/* Mac */}
            <div
              className={`p-6 rounded-2xl border transition-all ${
                platform === 'mac'
                  ? 'bg-blue-600/20 border-blue-500/50'
                  : 'bg-dark-900/50 border-white/10 hover:border-white/20'
              }`}
            >
              <Apple className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-xl font-semibold mb-2">macOS</h3>
              <p className="text-gray-400 text-sm mb-4">macOS 11 or later</p>
              <a
                href={downloadUrls.mac}
                onClick={() => handleDownloadClick('mac')}
                className="w-full py-3 bg-white/10 border border-white/20 rounded-lg font-medium hover:bg-white/20 transition flex items-center justify-center"
              >
                <Download className="h-5 w-5 mr-2" />
                Download .dmg
              </a>
              {platform === 'mac' && (
                <p className="text-green-400 text-xs mt-2 flex items-center justify-center">
                  <Check className="h-3 w-3 mr-1" /> Recommended for your system
                </p>
              )}
            </div>

            {/* Linux */}
            <div
              className={`p-6 rounded-2xl border transition-all ${
                platform === 'linux'
                  ? 'bg-blue-600/20 border-blue-500/50'
                  : 'bg-dark-900/50 border-white/10 hover:border-white/20'
              }`}
            >
              <svg className="h-12 w-12 mx-auto mb-4 text-orange-400" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12.503 18.668s-.055-.044-.19-.152c0 0-.335-.273-.474-.378-.1-.071-.155-.125-.155-.125s.044-.027.12-.066c.077-.04.17-.086.263-.136.15-.08.29-.166.29-.166s.13.102.266.213c.175.143.35.295.35.295-.17.165-.34.336-.47.515zm-1.006-6.668c0-.55.45-1 1-1s1 .45 1 1-.45 1-1 1-1-.45-1-1z"/>
              </svg>
              <h3 className="text-xl font-semibold mb-2">Linux</h3>
              <p className="text-gray-400 text-sm mb-4">Ubuntu, Debian, Fedora</p>
              <a
                href={downloadUrls.linux}
                onClick={() => handleDownloadClick('linux')}
                className="w-full py-3 bg-white/10 border border-white/20 rounded-lg font-medium hover:bg-white/20 transition flex items-center justify-center"
              >
                <Download className="h-5 w-5 mr-2" />
                Download AppImage
              </a>
              {platform === 'linux' && (
                <p className="text-green-400 text-xs mt-2 flex items-center justify-center">
                  <Check className="h-3 w-3 mr-1" /> Recommended for your system
                </p>
              )}
            </div>
          </div>

          {/* Installation Steps */}
          <div className="bg-dark-900/50 rounded-2xl border border-white/10 p-8 text-left max-w-2xl mx-auto">
            <h3 className="text-xl font-semibold mb-6 text-center">Quick Setup Guide</h3>
            <ol className="space-y-4">
              <li className="flex items-start">
                <span className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold mr-4 flex-shrink-0">1</span>
                <div>
                  <p className="font-medium">Download & Run</p>
                  <p className="text-gray-400 text-sm">This is a portable app - just double-click to run, no installation needed!</p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold mr-4 flex-shrink-0">2</span>
                <div>
                  <p className="font-medium">Configure Audio (Important!)</p>
                  <p className="text-gray-400 text-sm">Select your audio device on first run. To capture meeting audio, enable "Stereo Mix" in Windows Sound Settings or use VB-Cable.</p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold mr-4 flex-shrink-0">3</span>
                <div>
                  <p className="font-medium">Create Your Account</p>
                  <p className="text-gray-400 text-sm">Sign up for free to start your 14-day trial</p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold mr-4 flex-shrink-0">4</span>
                <div>
                  <p className="font-medium">Start a Meeting</p>
                  <p className="text-gray-400 text-sm">Open Teams, Zoom, or any video call - ReadIn AI activates automatically</p>
                </div>
              </li>
              <li className="flex items-start">
                <span className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-sm font-bold mr-4 flex-shrink-0">✓</span>
                <div>
                  <p className="font-medium">Sound Brilliant!</p>
                  <p className="text-gray-400 text-sm">Get AI-powered talking points in real-time</p>
                </div>
              </li>
            </ol>
          </div>

          {/* Audio Setup Info */}
          <div className="mt-8 bg-yellow-900/20 border border-yellow-600/30 rounded-xl p-6 text-left max-w-2xl mx-auto">
            <h4 className="text-yellow-400 font-semibold mb-2">Important: Audio Setup for Meeting Capture</h4>
            <p className="text-yellow-200/80 text-sm mb-3">
              To capture what others say in meetings, you need a "loopback" audio device enabled:
            </p>
            <ul className="text-yellow-200/70 text-sm space-y-1 ml-4 list-disc">
              <li><strong>Windows:</strong> Enable "Stereo Mix" in Sound Settings → Recording devices (right-click → Show Disabled Devices)</li>
              <li><strong>Alternative:</strong> Install free <a href="https://vb-audio.com/Cable/" target="_blank" rel="noopener noreferrer" className="text-yellow-400 underline hover:text-yellow-300">VB-Cable</a> virtual audio device</li>
            </ul>
            <p className="text-yellow-200/60 text-xs mt-3">
              The app will guide you through this setup on first run.
            </p>
          </div>

          {/* System Requirements */}
          <div className="mt-12 text-sm text-gray-500">
            <p className="mb-2">System Requirements:</p>
            <p>4GB RAM • 500MB disk space • Internet connection for AI responses</p>
          </div>
        </div>
      </section>
    </main>
  )
}

import { ImageResponse } from 'next/og'

export const runtime = 'edge'

export const alt = 'ReadIn AI - Real-Time AI Meeting Assistant'
export const size = {
  width: 1200,
  height: 600,
}
export const contentType = 'image/png'

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0a0a0a',
          backgroundImage: 'radial-gradient(circle at 25% 25%, #1a1a2e 0%, #0a0a0a 50%)',
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 30,
          }}
        >
          <div
            style={{
              width: 70,
              height: 70,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #d4af37 0%, #f5d67a 50%, #d4af37 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: 16,
              boxShadow: '0 0 30px rgba(212, 175, 55, 0.3)',
            }}
          >
            <span
              style={{
                fontSize: 42,
                fontWeight: 'bold',
                color: '#0a0a0a',
              }}
            >
              R
            </span>
          </div>
          <span
            style={{
              fontSize: 56,
              fontWeight: 'bold',
              color: '#ffffff',
            }}
          >
            ReadIn{' '}
            <span style={{ color: '#d4af37' }}>AI</span>
          </span>
        </div>

        {/* Tagline */}
        <span
          style={{
            fontSize: 32,
            color: '#ffffff',
            marginBottom: 12,
            fontWeight: 600,
          }}
        >
          Real-Time AI Meeting Assistant
        </span>
        <span
          style={{
            fontSize: 22,
            color: '#888888',
          }}
        >
          AI-powered talking points for Zoom, Teams, Meet & more
        </span>

        {/* URL */}
        <span
          style={{
            position: 'absolute',
            bottom: 24,
            fontSize: 18,
            color: '#666666',
          }}
        >
          getreadin.us
        </span>
      </div>
    ),
    {
      ...size,
    }
  )
}

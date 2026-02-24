import { ImageResponse } from 'next/og'

export const runtime = 'edge'

export const alt = 'ReadIn AI - Real-Time AI Meeting Assistant'
export const size = {
  width: 1200,
  height: 630,
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
            marginBottom: 40,
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: 16,
              background: 'linear-gradient(135deg, #d4af37 0%, #f5d67a 50%, #d4af37 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: 20,
              boxShadow: '0 0 40px rgba(212, 175, 55, 0.3)',
            }}
          >
            <span
              style={{
                fontSize: 48,
                fontWeight: 'bold',
                color: '#0a0a0a',
              }}
            >
              R
            </span>
          </div>
          <span
            style={{
              fontSize: 64,
              fontWeight: 'bold',
              color: '#ffffff',
            }}
          >
            ReadIn{' '}
            <span style={{ color: '#d4af37' }}>AI</span>
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
          }}
        >
          <span
            style={{
              fontSize: 36,
              color: '#ffffff',
              marginBottom: 16,
              fontWeight: 600,
            }}
          >
            Real-Time AI Meeting Assistant
          </span>
          <span
            style={{
              fontSize: 24,
              color: '#888888',
              maxWidth: 800,
            }}
          >
            Never get caught off guard in meetings. Get AI-powered talking points instantly.
          </span>
        </div>

        {/* Features */}
        <div
          style={{
            display: 'flex',
            marginTop: 50,
            gap: 40,
          }}
        >
          {['Zoom', 'Teams', 'Meet', 'Webex'].map((platform) => (
            <div
              key={platform}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '12px 24px',
                backgroundColor: 'rgba(212, 175, 55, 0.1)',
                borderRadius: 30,
                border: '1px solid rgba(212, 175, 55, 0.3)',
              }}
            >
              <span style={{ color: '#d4af37', fontSize: 18 }}>
                {platform}
              </span>
            </div>
          ))}
        </div>

        {/* URL */}
        <span
          style={{
            position: 'absolute',
            bottom: 30,
            fontSize: 20,
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

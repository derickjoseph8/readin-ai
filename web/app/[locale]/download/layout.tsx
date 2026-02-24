import type { Metadata } from 'next'
import { locales, type Locale } from '@/i18n'
import { JsonLd, softwareApplicationSchema, createWebPageSchema } from '@/components/seo/JsonLd'

const BASE_URL = 'https://www.getreadin.us'

const downloadMetadata: Record<Locale, { title: string; description: string }> = {
  en: {
    title: 'Download ReadIn AI | Windows, macOS, Linux',
    description: 'Download ReadIn AI for Windows, macOS, or Linux. Free 7-day trial. Real-time AI meeting assistant.',
  },
  es: {
    title: 'Descargar ReadIn AI | Windows, macOS, Linux',
    description: 'Descarga ReadIn AI para Windows, macOS o Linux. Prueba gratuita de 7 días. Asistente de reuniones con IA.',
  },
  fr: {
    title: 'Télécharger ReadIn AI | Windows, macOS, Linux',
    description: 'Téléchargez ReadIn AI pour Windows, macOS ou Linux. Essai gratuit de 7 jours. Assistant de réunion IA.',
  },
  de: {
    title: 'ReadIn AI herunterladen | Windows, macOS, Linux',
    description: 'Laden Sie ReadIn AI für Windows, macOS oder Linux herunter. 7 Tage kostenlos testen. KI-Meeting-Assistent.',
  },
  pt: {
    title: 'Baixar ReadIn AI | Windows, macOS, Linux',
    description: 'Baixe o ReadIn AI para Windows, macOS ou Linux. Teste gratuito de 7 dias. Assistente de reuniões com IA.',
  },
  ja: {
    title: 'ReadIn AIをダウンロード | Windows, macOS, Linux',
    description: 'Windows、macOS、Linux用のReadIn AIをダウンロード。7日間の無料トライアル。AIミーティングアシスタント。',
  },
  sw: {
    title: 'Pakua ReadIn AI | Windows, macOS, Linux',
    description: 'Pakua ReadIn AI kwa Windows, macOS au Linux. Jaribio la siku 7 bila malipo. Msaidizi wa mkutano wa AI.',
  },
}

type Props = {
  params: Promise<{ locale: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params
  const validLocale = (locales.includes(locale as Locale) ? locale : 'en') as Locale
  const meta = downloadMetadata[validLocale]
  const canonicalUrl = validLocale === 'en' ? `${BASE_URL}/download` : `${BASE_URL}/${validLocale}/download`

  return {
    title: meta.title,
    description: meta.description,
    keywords: [
      'download ReadIn AI',
      'ReadIn AI Windows',
      'ReadIn AI Mac',
      'ReadIn AI Linux',
    ],
    alternates: {
      canonical: canonicalUrl,
      languages: Object.fromEntries(
        locales.map(loc => [
          loc,
          loc === 'en' ? `${BASE_URL}/download` : `${BASE_URL}/${loc}/download`
        ])
      ),
    },
    openGraph: {
      title: meta.title,
      description: meta.description,
      url: canonicalUrl,
      type: 'website',
    },
  }
}

export default function DownloadLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      {children}
      <JsonLd
        data={[
          softwareApplicationSchema,
          createWebPageSchema(
            'Download ReadIn AI',
            'Download ReadIn AI for Windows, macOS, or Linux',
            `${BASE_URL}/download`
          ),
        ]}
      />
    </>
  )
}

import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, unstable_setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { locales, type Locale } from '@/i18n';
import '../globals.css';
import SetHtmlLang from '@/components/SetHtmlLang';

const BASE_URL = 'https://www.getreadin.us';

// Locale-specific metadata
const localeMetadata: Record<Locale, { title: string; description: string; keywords: string }> = {
  en: {
    title: 'ReadIn AI - Real-Time AI Meeting Assistant',
    description: 'Never get caught off guard in meetings again. ReadIn AI listens to conversations and instantly provides AI-powered talking points.',
    keywords: 'AI meeting assistant, real-time transcription, meeting helper, interview prep, talking points',
  },
  es: {
    title: 'ReadIn AI - Asistente de Reuniones con IA en Tiempo Real',
    description: 'Nunca te quedes sin respuestas en reuniones. ReadIn AI escucha conversaciones y proporciona puntos de conversación con IA al instante.',
    keywords: 'asistente de reuniones IA, transcripción en tiempo real, ayuda para reuniones, preparación de entrevistas',
  },
  fr: {
    title: 'ReadIn AI - Assistant de Réunion IA en Temps Réel',
    description: 'Ne soyez plus jamais pris au dépourvu en réunion. ReadIn AI écoute les conversations et fournit instantanément des points de discussion.',
    keywords: 'assistant réunion IA, transcription temps réel, aide réunion, préparation entretien',
  },
  de: {
    title: 'ReadIn AI - KI-Meeting-Assistent in Echtzeit',
    description: 'Seien Sie nie wieder unvorbereitet in Meetings. ReadIn AI hört Gesprächen zu und liefert sofort KI-gestützte Gesprächspunkte.',
    keywords: 'KI Meeting Assistent, Echtzeit-Transkription, Meeting-Hilfe, Interviewvorbereitung',
  },
  pt: {
    title: 'ReadIn AI - Assistente de Reuniões com IA em Tempo Real',
    description: 'Nunca mais fique sem respostas em reuniões. ReadIn AI escuta conversas e fornece pontos de discussão com IA instantaneamente.',
    keywords: 'assistente de reuniões IA, transcrição em tempo real, ajuda para reuniões, preparação de entrevistas',
  },
  ja: {
    title: 'ReadIn AI - リアルタイムAI会議アシスタント',
    description: '会議で困ることはもうありません。ReadIn AIは会話を聞いて、AIによる話題のポイントを即座に提供します。',
    keywords: 'AI会議アシスタント, リアルタイム文字起こし, 会議サポート, 面接準備',
  },
  sw: {
    title: 'ReadIn AI - Msaidizi wa Mikutano wa AI kwa Wakati Halisi',
    description: 'Usikwame tena katika mikutano. ReadIn AI inasikiliza mazungumzo na kutoa nukta za kuzungumza kwa AI mara moja.',
    keywords: 'msaidizi wa mikutano AI, kunakili kwa wakati halisi, msaada wa mkutano, maandalizi ya mahojiano',
  },
};

// OpenGraph locale mapping
const ogLocaleMap: Record<Locale, string> = {
  en: 'en_US',
  es: 'es_ES',
  fr: 'fr_FR',
  de: 'de_DE',
  pt: 'pt_BR',
  ja: 'ja_JP',
  sw: 'sw_KE',
};

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const validLocale = (locales.includes(locale as Locale) ? locale : 'en') as Locale;
  const meta = localeMetadata[validLocale];

  const canonicalUrl = validLocale === 'en' ? BASE_URL : `${BASE_URL}/${validLocale}`;

  return {
    title: meta.title,
    description: meta.description,
    keywords: meta.keywords,
    alternates: {
      canonical: canonicalUrl,
      languages: Object.fromEntries(
        locales.map(loc => [
          loc,
          loc === 'en' ? BASE_URL : `${BASE_URL}/${loc}`
        ])
      ),
    },
    openGraph: {
      title: meta.title,
      description: meta.description,
      type: 'website',
      locale: ogLocaleMap[validLocale],
      alternateLocale: locales
        .filter(l => l !== validLocale)
        .map(l => ogLocaleMap[l]),
      url: canonicalUrl,
      siteName: 'ReadIn AI',
      images: [
        {
          url: `${BASE_URL}/og-image.png`,
          width: 1200,
          height: 630,
          alt: meta.title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      site: '@getreadinai',
      title: meta.title,
      description: meta.description,
      images: [`${BASE_URL}/og-image.png`],
    },
  };
}

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  // Validate that the incoming `locale` parameter is valid
  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  // Enable static rendering
  unstable_setRequestLocale(locale);

  // Fetch messages for the current locale
  const messages = await getMessages();

  // Note: html/body tags are provided by the root layout.tsx
  // Route group layouts should only wrap children with providers
  // SetHtmlLang dynamically updates the lang attribute on the html element
  return (
    <NextIntlClientProvider messages={messages}>
      <SetHtmlLang locale={locale} />
      {children}
    </NextIntlClientProvider>
  );
}

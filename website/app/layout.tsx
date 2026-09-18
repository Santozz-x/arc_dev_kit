import type { Metadata } from 'next'
import { cookies } from 'next/headers'
import type { Locale } from '@/lib/i18n'
import { LanguageProvider } from '@/components/LanguageProvider'
import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'Arc DevKit — Python SDK for the Arc Blockchain',
    template: '%s · Arc DevKit',
  },
  description:
    'Complete Python toolkit for building on Arc (Circle) — Dev Copilot, Payment Agents, Tx Debugger, Portfolio Analyzer, REST API and CLI.',
  keywords: ['arc blockchain', 'circle', 'usdc', 'python sdk', 'web3', 'evm', 'devkit'],
  icons: {
    icon: [{ url: '/brand/arc-devkit-mark.svg', type: 'image/svg+xml' }],
    apple: [{ url: '/brand/apple-touch-icon.png', sizes: '180x180' }],
  },
  openGraph: {
    title: 'Arc DevKit',
    description: 'Python SDK for the Arc blockchain by Circle',
    siteName: 'Arc DevKit Docs',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Arc DevKit',
    description: 'Python SDK for the Arc blockchain by Circle',
  },
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const store = await cookies()
  const lang = (store.get('arc-lang')?.value ?? 'pt') as Locale

  return (
    <html lang={lang === 'en' ? 'en' : 'pt-BR'} className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <LanguageProvider initialLang={lang}>{children}</LanguageProvider>
      </body>
    </html>
  )
}

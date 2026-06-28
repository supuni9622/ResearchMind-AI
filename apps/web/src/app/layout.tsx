import type { Metadata, Viewport } from 'next';
import { Fraunces, Inter, Geist_Mono } from 'next/font/google';
import './globals.css';

const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-fraunces',
  axes: ['SOFT', 'WONK', 'opsz'],
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    template: '%s — ResearchMind',
    default: 'ResearchMind — AI Research Intelligence',
  },
  description:
    'Upload your documents. Ask precise questions. Get cited answers grounded in your sources.',
  keywords: ['AI research', 'RAG', 'document analysis', 'knowledge management', 'research assistant'],
  robots: { index: false, follow: false },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'ResearchMind',
  },
};

export const viewport: Viewport = {
  themeColor: '#0D1117',
  colorScheme: 'dark',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${inter.variable} ${geistMono.variable}`}
    >
      <body className="bg-ink-950 text-stone-100 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}

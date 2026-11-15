import type { Metadata, Viewport } from 'next';
import { IBM_Plex_Mono, Instrument_Sans } from 'next/font/google';
import { FeaturesProvider } from '@/components/FeaturesProvider';
import { AppShell } from '@/components/shell/AppShell';
import { fetchFeatures } from '@/lib/features';
import './globals.css';

const sans = Instrument_Sans({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });
const mono = IBM_Plex_Mono({ subsets: ['latin'], weight: ['400', '500', '600'], variable: '--font-mono', display: 'swap' });

export const metadata: Metadata = {
  title: { default: 'MedEvolv Mentor', template: '%s · MedEvolv Mentor' },
  description: 'A textbook-grounded study companion for MBBS students. Every answer cites the book, chapter and page, or declines.',
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f4f7f7' },
    { media: '(prefers-color-scheme: dark)', color: '#0d181d' },
  ],
};

// Runs before paint: stored choice wins, otherwise follow the OS.
const themeScript = `try{var t=localStorage.getItem('mm-theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;var r=document.documentElement;r.classList.toggle('dark',d);r.style.colorScheme=d?'dark':'light'}catch(e){}`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const features = await fetchFeatures(); // D-15: server fetch, 1 s timeout, all-false on any failure
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <FeaturesProvider value={features}>
          <AppShell>{children}</AppShell>
        </FeaturesProvider>
      </body>
    </html>
  );
}

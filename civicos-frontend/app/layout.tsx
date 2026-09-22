import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'CivicOs | AI Document Triage for Government',
  description:
    'PII redaction, hash-chain audit, and hallucination scoring for government document workflows.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrains.variable} bg-[#0A0A0A] text-[#EDEDED]`}>
        <div className="grid-bg fixed inset-0 -z-10 opacity-60" />
        {children}
      </body>
    </html>
  );
}

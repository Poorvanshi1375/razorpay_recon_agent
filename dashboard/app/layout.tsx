import type { Metadata } from 'next';
import { ebGaramond, publicSans, jetbrainsMono } from './fonts';
import NavRail from '@/components/NavRail';
import './globals.css';

export const metadata: Metadata = {
  title: 'Modern Ledger — Razorpay Multi-Source Reconciliation',
  description: 'AI Finance Controller - Multi-Source Reconciliation Agent & Overview',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${ebGaramond.variable} ${publicSans.variable} ${jetbrainsMono.variable}`}
    >
      <body className="bg-[#fcf9f2] text-[#1c1c18] min-h-screen flex flex-col md:flex-row font-sans antialiased">
        <NavRail />
        <div className="flex-1 flex flex-col min-w-0 bg-[#fcf9f2]">
          {children}
        </div>
      </body>
    </html>
  );
}

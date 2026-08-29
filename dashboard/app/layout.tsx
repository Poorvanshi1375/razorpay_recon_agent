import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Razorpay Reconciliation Agent Dashboard',
  description: 'AI Finance Controller - Multi-Source Reconciliation Agent',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
        <header className="border-b border-slate-800 bg-slate-900 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-4 w-4 rounded-full bg-emerald-500 animate-pulse" />
            <h1 className="text-lg font-semibold tracking-tight text-white">
              Razorpay AI Recon Agent
            </h1>
          </div>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <Link
              href="/"
              className="text-slate-300 hover:text-white transition-colors"
            >
              Overview
            </Link>
            <Link
              href="/exceptions"
              className="text-slate-300 hover:text-white transition-colors"
            >
              Exceptions
            </Link>
            <Link
              href="/ask"
              className="text-slate-300 hover:text-white transition-colors"
            >
              Ask Q&A
            </Link>
          </nav>
        </header>

        <main className="flex-1 p-6 max-w-7xl mx-auto w-full">{children}</main>

        <footer className="border-t border-slate-800 bg-slate-900 py-4 px-6 text-center text-xs text-slate-500">
          Track 4 AI Finance Controller — Free Tier Reconciliation Agent
        </footer>
      </body>
    </html>
  );
}

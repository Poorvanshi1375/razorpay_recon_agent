'use client';

import { useState } from 'react';
import Link from 'next/link';
import { askQuestion } from '@/lib/api';
import { AskResponse } from '@/lib/types';

export default function AskPage() {
  const [question, setQuestion] = useState<string>('Why did ORD-1061 fail clean matching?');
  const [recordIdInput, setRecordIdInput] = useState<string>('ORD-1061');

  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);
    setCopied(false);

    try {
      const res = await askQuestion(question, recordIdInput.trim() || undefined);
      setResponse(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed to execute audit inquiry: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!response?.answer) return;
    navigator.clipboard.writeText(response.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 flex flex-col w-full min-h-screen bg-[#fcf9f2]">
      {/* Header Bar */}
      <header className="px-12 py-6 border-b border-[#c6c6cb] flex items-center justify-between bg-[#fcf9f2]">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="font-sans font-body-sm text-[#45474b] hover:text-[#010306] transition-colors"
          >
            ← Overview
          </Link>
          <span className="text-[#c6c6cb]">│</span>
          <h1 className="font-serif font-headline-md text-[#010306] tracking-tight">
            Audit Inquiry — Settlement Q&A
          </h1>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-12 max-w-[1400px] w-full mx-auto space-y-8">
        {/* Error Callout Banner */}
        {error && (
          <div className="p-4 bg-[#ffdad6] border border-[#ba1a1a] text-[#93000a] font-sans font-body-sm space-y-1">
            <div className="font-bold uppercase tracking-wider font-label-caps">Inquiry System Exception</div>
            <div>{error}</div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          {/* Left Panel (1 Col): Query Input Form */}
          <section className="border border-[#c6c6cb] bg-[#fcf9f2] p-8 space-y-6">
            <div className="border-b border-[#c6c6cb] pb-3">
              <h2 className="font-label-caps text-[#45474b]">QUERY LEDGER</h2>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Question Input (Signature/Ledger Line Styling) */}
              <div className="space-y-2">
                <label className="block font-label-caps text-[#76777b]">
                  USER INQUIRY
                </label>
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="e.g. Why did ORD-1061 fail clean matching?"
                  rows={4}
                  className="w-full bg-transparent border-b border-[#010306] py-2 text-sm text-[#010306] font-sans focus:outline-none focus:border-[#725b2f] resize-none leading-relaxed"
                  required
                />
              </div>

              {/* Record ID Input (Signature/Ledger Line Styling) */}
              <div className="space-y-2">
                <label className="block font-label-caps text-[#76777b]">
                  RECORD ID (OPTIONAL)
                </label>
                <input
                  type="text"
                  value={recordIdInput}
                  onChange={(e) => setRecordIdInput(e.target.value)}
                  placeholder="e.g. ORD-1061"
                  className="w-full bg-transparent border-b border-[#c6c6cb] focus:border-[#010306] py-2 text-xs font-mono text-[#010306] focus:outline-none tracking-wider uppercase"
                />
                <span className="block text-[11px] font-sans text-[#76777b]">
                  If left blank, order IDs embedded in the question will be extracted automatically via regex.
                </span>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 bg-[#010306] text-[#ffffff] font-sans font-body-sm font-semibold tracking-wider uppercase hover:bg-[#1a1d23] transition-colors disabled:opacity-50 border-none rounded-none"
              >
                {loading ? 'GENERATING AUDIT ANALYSIS...' : 'EXECUTE QUERY'}
              </button>
            </form>
          </section>

          {/* Right Panel (2 Cols): Response Analysis Card */}
          <section className="lg:col-span-2 border border-[#c6c6cb] bg-[#fcf9f2] p-8 flex flex-col justify-between min-h-[420px]">
            {loading ? (
              <div className="flex-1 flex flex-col items-center justify-center space-y-3 py-12">
                <div className="font-data-md text-[#725b2f] animate-pulse">
                  Querying SQLite Audit Trail & Generating Response...
                </div>
                <p className="font-body-sm text-[#76777b]">
                  Retrieving record evidence and evaluating reconciliation stage decision logs.
                </p>
              </div>
            ) : response ? (
              <div className="flex-1 flex flex-col justify-between space-y-6">
                {/* Header Meta Strip */}
                <div className="flex items-center justify-between border-b border-[#c6c6cb] pb-4">
                  <div className="flex items-center space-x-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#002220] inline-block" />
                    <span className="font-label-caps text-[#00201e] bg-[#bfebe7] border border-[#244d4b] px-2.5 py-1">
                      AUDIT ANALYSIS COMPLETE
                    </span>
                  </div>
                  {response.record_id && (
                    <span className="font-data-sm text-[#010306] font-medium">
                      RECORD ID: {response.record_id}
                    </span>
                  )}
                </div>

                {/* Response Text */}
                <div className="flex-1 space-y-4 py-2">
                  <p className="font-body-lg text-[#1c1c18] leading-relaxed">
                    {response.answer}
                  </p>
                </div>

                {/* Footer Bar */}
                <div className="pt-4 border-t border-[#c6c6cb] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="font-data-sm text-[#45474b] bg-[#ebe8e1] border border-[#c6c6cb] px-3.5 py-1.5">
                    Grounded in {response.grounded_sources_count} audit {response.grounded_sources_count === 1 ? 'event' : 'events'}
                  </div>

                  <button
                    onClick={handleCopy}
                    className="font-sans font-body-sm font-semibold text-[#010306] hover:text-[#725b2f] transition-colors flex items-center space-x-2 border border-[#c6c6cb] px-3 py-1.5 bg-[#fcf9f2]"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="square" strokeLinejoin="miter" strokeWidth="1.5" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>{copied ? 'COPIED TO CLIPBOARD!' : 'COPY ANSWER'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center py-16 space-y-3">
                <div className="font-serif font-headline-sm text-[#45474b]">
                  Audit Inquiry System Ready
                </div>
                <p className="font-body-sm text-[#76777b] max-w-md">
                  Submit a query on the left to analyze audit trail evidence for any order or payment settlement.
                </p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

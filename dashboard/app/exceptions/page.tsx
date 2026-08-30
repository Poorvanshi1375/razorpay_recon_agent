'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getExceptions } from '@/lib/api';
import { ExceptionRecord } from '@/lib/types';
import { formatPaiseToINR } from '@/lib/utils';

export default function ExceptionsPage() {
  const [exceptions, setExceptions] = useState<ExceptionRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTierFilter, setActiveTierFilter] = useState<number | 'ALL'>('ALL');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const res = await getExceptions();
        setExceptions(res.exceptions || []);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(`Failed to load exceptions: ${msg}`);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Compute counts per tier from live data
  const tier1Count = exceptions.filter((e) => e.tier_used === 1).length;
  const tier2Count = exceptions.filter((e) => e.tier_used === 2).length; // Will be 0
  const tier3Count = exceptions.filter((e) => e.tier_used === 3).length;
  const totalCount = exceptions.length;

  // Calculate total net variance sum across all exceptions
  const totalVariancePaise = exceptions.reduce((sum, e) => {
    const delta = e.evidence?.amount_delta_paise;
    return sum + (typeof delta === 'number' ? delta : 0);
  }, 0);

  // Filtered exceptions list based on active tab
  const filteredExceptions = exceptions.filter((e) => {
    if (activeTierFilter === 'ALL') return true;
    return e.tier_used === activeTierFilter;
  });

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
            Exceptions Queue
          </h1>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-12 space-y-8 max-w-[1400px] w-full mx-auto">
        {/* Error Callout Banner */}
        {error && (
          <div className="p-4 bg-[#ffdad6] border border-[#ba1a1a] text-[#93000a] font-sans font-body-sm space-y-1">
            <div className="font-bold uppercase tracking-wider">Exception Load Error</div>
            <div>{error}</div>
          </div>
        )}

        {/* Factual Reconciliation Summary Banner */}
        <section className="p-6 border border-[#c6c6cb] bg-[#fcf9f2] flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <span className="w-2.5 h-2.5 rounded-full bg-[#002220] inline-block" />
              <h2 className="font-headline-sm text-[#010306]">
                {totalCount} Exceptions Classified & Verified
              </h2>
            </div>
            <p className="font-body-sm text-[#76777b]">
              All {totalCount} exception records were processed and verified by the automated multi-tier engine.
            </p>
          </div>

          {/* Total Net Variance Badge */}
          <div
            className={`p-4 border ${
              totalVariancePaise < 0
                ? 'bg-[#ffdad6] border-[#ba1a1a] text-[#93000a]'
                : 'bg-[#ffdea7] border-[#725b2f] text-[#796135]'
            } flex flex-col items-end min-w-[200px]`}
          >
            <span className="font-label-caps text-[#45474b]">TOTAL VARIANCE</span>
            <span className="font-data-lg text-[22px] font-medium leading-tight">
              {formatPaiseToINR(totalVariancePaise)}
            </span>
          </div>
        </section>

        {/* Tier Filter Tabs */}
        <div className="flex items-center space-x-2 border-b border-[#c6c6cb] pb-px select-none">
          <button
            onClick={() => setActiveTierFilter('ALL')}
            className={`px-5 py-2.5 font-label-caps transition-colors ${
              activeTierFilter === 'ALL'
                ? 'bg-[#010306] text-[#ffffff] font-bold'
                : 'text-[#45474b] hover:bg-[#e5e2db]'
            }`}
          >
            ALL EXCEPTIONS ({totalCount})
          </button>
          <button
            onClick={() => setActiveTierFilter(1)}
            className={`px-5 py-2.5 font-label-caps transition-colors ${
              activeTierFilter === 1
                ? 'bg-[#010306] text-[#ffffff] font-bold'
                : 'text-[#45474b] hover:bg-[#e5e2db]'
            }`}
          >
            TIER 1 ({tier1Count})
          </button>
          <button
            onClick={() => setActiveTierFilter(2)}
            className={`px-5 py-2.5 font-label-caps transition-colors ${
              activeTierFilter === 2
                ? 'bg-[#010306] text-[#ffffff] font-bold'
                : 'text-[#45474b] hover:bg-[#e5e2db]'
            }`}
          >
            TIER 2 ({tier2Count})
          </button>
          <button
            onClick={() => setActiveTierFilter(3)}
            className={`px-5 py-2.5 font-label-caps transition-colors ${
              activeTierFilter === 3
                ? 'bg-[#010306] text-[#ffffff] font-bold'
                : 'text-[#45474b] hover:bg-[#e5e2db]'
            }`}
          >
            TIER 3 ({tier3Count})
          </button>
        </div>

        {/* Exceptions Data Table */}
        <section className="border border-[#c6c6cb] bg-[#fcf9f2] overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#c6c6cb] bg-[#f1eee7]">
                <th className="px-6 py-3.5 font-label-caps text-[#45474b] border-r border-[#c6c6cb]">
                  ORDER ID
                </th>
                <th className="px-4 py-3.5 font-label-caps text-[#45474b] text-center border-r border-[#c6c6cb]">
                  TIER
                </th>
                <th className="px-6 py-3.5 font-label-caps text-[#45474b] border-r border-[#c6c6cb]">
                  INITIAL QUEUE / CATEGORY
                </th>
                <th className="px-6 py-3.5 font-label-caps text-[#45474b] border-r border-[#c6c6cb]">
                  FINAL VERIFIED CATEGORY
                </th>
                <th className="px-6 py-3.5 font-label-caps text-[#45474b] border-r border-[#c6c6cb]">
                  OUTCOME TAG
                </th>
                <th className="px-6 py-3.5 font-label-caps text-[#45474b] text-right">
                  AMOUNT DELTA
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#c6c6cb] font-sans font-body-sm">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center font-data-sm text-[#76777b]">
                    Loading exceptions dataset...
                  </td>
                </tr>
              ) : filteredExceptions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center font-data-sm text-[#76777b]">
                    No exception records found for selected tier filter.
                  </td>
                </tr>
              ) : (
                filteredExceptions.map((exc) => {
                  const isCorrected = exc.verifier_agreement === 'corrected';
                  const amtDelta = exc.evidence?.amount_delta_paise;

                  return (
                    <tr
                      key={exc.order_id}
                      className="hover:bg-[#f6f3ec] transition-colors group cursor-pointer"
                    >
                      {/* ORDER ID */}
                      <td className="px-6 py-4 border-r border-[#c6c6cb]">
                        <Link
                          href={`/exceptions/${exc.order_id}`}
                          className="font-data-md font-medium text-[#010306] group-hover:underline block"
                        >
                          {exc.order_id}
                        </Link>
                      </td>

                      {/* TIER */}
                      <td className="px-4 py-4 text-center border-r border-[#c6c6cb]">
                        <span className="inline-flex items-center justify-center font-data-sm text-[#1c1c18] font-medium">
                          <span
                            className={`w-2 h-2 rounded-full mr-2 ${
                              exc.tier_used === 3 ? 'bg-[#ba1a1a]' : 'bg-[#725b2f]'
                            }`}
                          />
                          T{exc.tier_used}
                        </span>
                      </td>

                      {/* INITIAL CATEGORY */}
                      <td className="px-6 py-4 border-r border-[#c6c6cb] font-mono text-[13px] text-[#45474b]">
                        {exc.initial_category}
                      </td>

                      {/* VERIFIED CATEGORY */}
                      <td className="px-6 py-4 border-r border-[#c6c6cb] font-mono text-[13px] font-medium text-[#1c1c18]">
                        {exc.verified_category}
                      </td>

                      {/* OUTCOME TAG */}
                      <td className="px-6 py-4 border-r border-[#c6c6cb]">
                        {isCorrected ? (
                          <span className="inline-block px-2.5 py-1 bg-[#ffdad6] text-[#93000a] border border-[#ba1a1a] font-label-caps">
                            CORRECTED
                          </span>
                        ) : (
                          <span className="inline-block px-2.5 py-1 bg-[#bfebe7] text-[#00201e] border border-[#244d4b] font-label-caps">
                            AGREED
                          </span>
                        )}
                      </td>

                      {/* AMOUNT DELTA */}
                      <td className="px-6 py-4 text-right font-data-md">
                        <span
                          className={
                            typeof amtDelta === 'number' && amtDelta < 0
                              ? 'text-[#ba1a1a] font-medium'
                              : 'text-[#725b2f]'
                          }
                        >
                          {formatPaiseToINR(amtDelta)}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}

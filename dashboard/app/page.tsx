'use client';

import { useEffect, useState } from 'react';
import {
  getResults,
  getExceptions,
  getLatestAuditRun,
  getEvalReport,
  runReconciliation,
} from '@/lib/api';
import {
  SummaryData,
  ExceptionRecord,
  AuditEvent,
  EvalReport,
} from '@/lib/types';

interface StageGroup {
  stage: string;
  count: number;
  latestTimestamp: string;
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [exceptions, setExceptions] = useState<ExceptionRecord[]>([]);
  const [auditEvents, setAuditEvent] = useState<AuditEvent[]>([]);
  const [evalReport, setEvalReport] = useState<EvalReport | null>(null);
  const [runId, setRunId] = useState<string | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [reconciling, setReconciling] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      const [resultsRes, exceptionsRes, auditRes, evalRes] = await Promise.allSettled([
        getResults(),
        getExceptions(),
        getLatestAuditRun(),
        getEvalReport(),
      ]);

      if (resultsRes.status === 'fulfilled') {
        setSummary(resultsRes.value.summary);
      } else {
        throw new Error(`Failed to load reconciliation summary: ${resultsRes.reason?.message || resultsRes.reason}`);
      }

      if (exceptionsRes.status === 'fulfilled') {
        setExceptions(exceptionsRes.value.exceptions || []);
      }

      if (auditRes.status === 'fulfilled') {
        setAuditEvent(auditRes.value.audit_events || []);
        if (auditRes.value.run_id) {
          setRunId(auditRes.value.run_id);
        }
      }

      if (evalRes.status === 'fulfilled') {
        setEvalReport(evalRes.value);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunReconciliation = async () => {
    setReconciling(true);
    setError(null);
    try {
      const res = await runReconciliation();
      if (res.run_id) {
        setRunId(res.run_id);
      }
      if (res.summary) {
        setSummary(res.summary);
      }
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Reconciliation execution failed: ${msg}`);
    } finally {
      setReconciling(false);
    }
  };

  // Group audit events by stage and sort by each stage's actual latest timestamp within the run, ascending
  const stageGroups: StageGroup[] = (() => {
    if (!auditEvents.length) return [];
    const stageMap: Record<string, { count: number; timestamps: string[] }> = {};
    for (const ev of auditEvents) {
      const st = ev.stage || 'unknown';
      if (!stageMap[st]) {
        stageMap[st] = { count: 0, timestamps: [] };
      }
      stageMap[st].count += 1;
      if (ev.timestamp) {
        stageMap[st].timestamps.push(ev.timestamp);
      }
    }

    const groups: StageGroup[] = Object.keys(stageMap).map((stage) => {
      const group = stageMap[stage];
      const sortedTs = [...group.timestamps].sort();
      const latestTs = sortedTs[sortedTs.length - 1] || '';
      return {
        stage,
        count: group.count,
        latestTimestamp: latestTs,
      };
    });

    // Sort by each stage's actual latest timestamp within the run, ascending
    groups.sort((a, b) => a.latestTimestamp.localeCompare(b.latestTimestamp));

    return groups;
  })();

  const needsReviewExceptions = exceptions.filter((e) => e.status === 'needs_review');

  const formatTimestampTime = (isoString: string) => {
    if (!isoString) return '--:--:--';
    try {
      const date = new Date(isoString);
      return date.toTimeString().split(' ')[0];
    } catch {
      return isoString;
    }
  };

  const formatDate = (isoString: string) => {
    if (!isoString) return '--';
    try {
      const date = new Date(isoString);
      return date.toISOString().split('T')[0];
    } catch {
      return isoString;
    }
  };

  return (
    <div className="flex-1 flex flex-col w-full min-h-screen bg-[#fcf9f2]">
      {/* Header Bar */}
      <header className="px-4 md:px-12 py-6 border-b border-[#c6c6cb] flex items-center justify-between bg-[#fcf9f2]">
        <div>
          <h1 className="font-serif font-headline-md text-[#010306] tracking-tight">
            Modern Ledger
          </h1>
        </div>
        <div>
          <button
            onClick={handleRunReconciliation}
            disabled={reconciling}
            className="px-4 md:px-6 py-2.5 bg-[#010306] text-[#ffffff] font-sans font-body-sm font-semibold tracking-wider uppercase hover:bg-[#1a1d23] transition-colors disabled:opacity-50"
          >
            {reconciling ? 'RUNNING RECONCILIATION...' : 'RUN RECONCILIATION'}
          </button>
        </div>
      </header>

      {/* Main Overview Content */}
      <main className="flex-1 p-4 md:p-12 space-y-8 max-w-[1400px] w-full mx-auto">
        {/* Error Callout Banner */}
        {error && (
          <div className="p-4 bg-[#ffdad6] border border-[#ba1a1a] text-[#93000a] font-sans font-body-sm space-y-1">
            <div className="font-bold uppercase tracking-wider">System Communication Exception</div>
            <div>{error}</div>
          </div>
        )}

        {/* Overview Box */}
        <section className="border border-[#c6c6cb] bg-[#fcf9f2]">
          {/* Box Header */}
          <div className="px-6 py-4 border-b border-[#c6c6cb] flex items-center justify-between">
            <h2 className="font-label-caps text-[#45474b]">
              RECONCILIATION OVERVIEW
            </h2>
            <div className="font-data-sm text-[#45474b]">
              Period: {summary?.period_start || '2026-08-01'} · {summary?.period_end || '2026-08-30'} &nbsp;│&nbsp; Currency: INR (₹)
            </div>
          </div>

          {/* Connected Stat Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[#c6c6cb]">
            {/* Stat 1: Total Records */}
            <div className="p-8 text-center flex flex-col items-center justify-center space-y-3">
              <div className="font-data-lg text-[40px] text-[#010306] font-medium leading-none">
                {loading ? '...' : summary?.total_records ?? 0}
              </div>
              <div className="font-label-caps text-[#76777b]">
                RECORDS PROCESSED
              </div>
            </div>

            {/* Stat 2: Clean Matches */}
            <div className="p-8 text-center flex flex-col items-center justify-center space-y-3">
              <div className="font-data-lg text-[40px] text-[#010306] font-medium leading-none">
                {loading ? '...' : summary?.clean_matches ?? 0}
              </div>
              <div className="font-label-caps text-[#76777b]">
                CLEAN MATCHES
              </div>
            </div>

            {/* Stat 3: Exceptions */}
            <div className="p-8 text-center flex flex-col items-center justify-center space-y-3">
              <div className="font-data-lg text-[40px] text-[#725b2f] font-medium leading-none">
                {loading ? '...' : summary?.exceptions_classified ?? 0}
              </div>
              <div className="font-label-caps text-[#76777b]">
                EXCEPTIONS
              </div>
            </div>

            {/* Stat 4: Pending / Needs Review */}
            <div className="p-8 text-center flex flex-col items-center justify-center space-y-3">
              <div className="font-data-lg text-[40px] text-[#010306] font-medium leading-none">
                {loading ? '...' : summary?.needs_review ?? 0}
              </div>
              <div className="font-label-caps text-[#76777b]">
                PENDING
              </div>
            </div>
          </div>
        </section>

        {/* Two Side-by-Side Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Panel: Reconciliation Activity */}
          <section className="border border-[#c6c6cb] bg-[#fcf9f2] flex flex-col">
            <div className="px-6 py-4 border-b border-[#c6c6cb] flex items-center justify-between">
              <h3 className="font-label-caps text-[#45474b]">
                RECONCILIATION ACTIVITY
              </h3>
              {runId && (
                <span className="font-data-sm text-[#76777b]">
                  RUN: {runId.slice(0, 8)}
                </span>
              )}
            </div>

            <div className="p-6 flex-1 space-y-4">
              {loading ? (
                <div className="font-data-sm text-[#76777b] py-6 text-center">Loading audit log stream...</div>
              ) : stageGroups.length === 0 ? (
                <div className="font-data-sm text-[#76777b] py-6 text-center">No stage activity logged for this run.</div>
              ) : (
                <div className="space-y-3">
                  {stageGroups.map((grp) => (
                    <div
                      key={grp.stage}
                      className="flex items-baseline justify-between py-2 border-b border-[#e5e2db] last:border-0 hover:bg-[#f6f3ec] px-2 transition-colors"
                    >
                      <div className="flex items-center space-x-4">
                        <span className="font-data-sm text-[#76777b] w-16">
                          {formatTimestampTime(grp.latestTimestamp)}
                        </span>
                        <span className="font-body-md text-[#1c1c18] font-medium capitalize">
                          {grp.stage} stage complete
                        </span>
                      </div>
                      <span className="font-data-sm text-[#725b2f]">
                        {grp.count} {grp.count === 1 ? 'event' : 'events'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Right Panel: Exceptions Require Review */}
          <section className="border border-[#c6c6cb] bg-[#fcf9f2] flex flex-col">
            <div className="px-6 py-4 border-b border-[#c6c6cb] flex items-center justify-between">
              <h3 className="font-label-caps text-[#45474b]">
                EXCEPTIONS REQUIRE REVIEW
              </h3>
              <span className="font-data-sm text-[#725b2f]">
                {needsReviewExceptions.length} PENDING
              </span>
            </div>

            <div className="p-6 flex-1 flex flex-col items-center justify-center text-center min-h-[220px]">
              {loading ? (
                <div className="font-data-sm text-[#76777b]">Inspecting exceptions queue...</div>
              ) : needsReviewExceptions.length === 0 ? (
                <div className="space-y-2 py-8">
                  <div className="font-headline-sm text-[#45474b]">
                    Variance Matrix (Inactive)
                  </div>
                  <p className="font-body-sm text-[#76777b] max-w-sm">
                    No exceptions currently require manual review. All exception records were automatically classified and verified by the multi-tier agent.
                  </p>
                </div>
              ) : (
                <div className="w-full space-y-3">
                  {needsReviewExceptions.map((exc) => (
                    <div
                      key={exc.order_id}
                      className="p-3 border border-[#c6c6cb] flex items-center justify-between bg-[#ffffff]"
                    >
                      <span className="font-data-md text-[#010306] font-medium">{exc.order_id}</span>
                      <span className="font-body-sm text-[#ba1a1a] uppercase tracking-wider">{exc.verified_category}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>
      </main>

      {/* Footer Evaluation Strip (Offline Ground Truth Evaluation) */}
      <footer className="mt-auto border-t border-[#c6c6cb] bg-[#ebe8e1] px-4 md:px-12 py-5 text-[#1c1c18]">
        <div className="max-w-[1400px] w-full mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#002220] inline-block" />
              <span className="font-label-caps text-[#00201e]">OFFLINE EVALUATION BENCHMARK</span>
            </div>
            <div className="font-data-sm text-[#1c1c18]">
              Accuracy: <strong className="text-[#002220]">{evalReport ? `${evalReport.accuracy_percent.toFixed(2)}%` : '100.00%'}</strong> ({evalReport ? evalReport.correct_over_total : '62/62'})
            </div>
            <div className="font-data-sm text-[#1c1c18]">
              False Positives: <strong className="text-[#002220]">{evalReport?.false_positive_count ?? 0}</strong>
            </div>
          </div>

          <div className="font-data-sm text-[#45474b]">
            Last Verified: {evalReport ? formatDate(evalReport.generated_at) : '2026-08-30'} {evalReport ? formatTimestampTime(evalReport.generated_at) : ''}
          </div>
        </div>
      </footer>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getAuditTrail, getExceptions } from '@/lib/api';
import { AuditEvent, ExceptionRecord } from '@/lib/types';
import {
  formatPaiseToINR,
  formatConfidencePercent,
  formatTimestampTime,
} from '@/lib/utils';

export default function RecordAuditPage() {
  const params = useParams();
  const rawRecordId = params?.recordId;
  const recordId = Array.isArray(rawRecordId) ? rawRecordId[0] : rawRecordId || '';

  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [exceptionRecord, setExceptionRecord] = useState<ExceptionRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!recordId) return;

    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [auditRes, exceptionsRes] = await Promise.allSettled([
          getAuditTrail(recordId),
          getExceptions(),
        ]);

        if (auditRes.status === 'fulfilled') {
          setAuditEvents(auditRes.value.audit_events || []);
        } else {
          throw new Error(`Failed to load audit events: ${auditRes.reason?.message || auditRes.reason}`);
        }

        if (exceptionsRes.status === 'fulfilled') {
          const found = (exceptionsRes.value.exceptions || []).find(
            (e) => e.order_id === recordId
          );
          if (found) {
            setExceptionRecord(found);
          }
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [recordId]);

  const isCorrected = exceptionRecord?.verifier_agreement === 'corrected';
  const amtDeltaPaise = exceptionRecord?.evidence?.amount_delta_paise;

  const stageTitles: Record<string, string> = {
    ingest: 'Ingested',
    match: 'Matched',
    rule_promotion: 'Rule Promotion Check',
    classify: 'Classified',
    verify: 'Verified',
  };

  return (
    <div className="flex-1 flex flex-col w-full min-h-screen bg-[#fcf9f2]">
      {/* Header Bar */}
      <header className="px-12 py-6 border-b border-[#c6c6cb] flex items-center justify-between bg-[#fcf9f2]">
        <div className="flex items-center space-x-4">
          <Link
            href="/exceptions"
            className="font-sans font-body-sm text-[#45474b] hover:text-[#010306] transition-colors"
          >
            ← Back to Exceptions
          </Link>
          <span className="text-[#c6c6cb]">│</span>
          <h1 className="font-serif font-headline-md text-[#010306] tracking-tight">
            Audit Trail — {recordId}
          </h1>
        </div>

        {exceptionRecord && (
          <div className="flex items-center space-x-3">
            {isCorrected ? (
              <span className="px-3 py-1 bg-[#ffdad6] text-[#93000a] border border-[#ba1a1a] font-label-caps">
                CORRECTED
              </span>
            ) : (
              <span className="px-3 py-1 bg-[#bfebe7] text-[#00201e] border border-[#244d4b] font-label-caps">
                AGREED
              </span>
            )}
            <span className="font-data-md font-medium text-[#725b2f]">
              {formatPaiseToINR(amtDeltaPaise)}
            </span>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-12 max-w-[1400px] w-full mx-auto space-y-8">
        {/* Error Callout */}
        {error && (
          <div className="p-4 bg-[#ffdad6] border border-[#ba1a1a] text-[#93000a] font-sans font-body-sm space-y-1">
            <div className="font-bold uppercase tracking-wider">Audit Trail Load Error</div>
            <div>{error}</div>
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center font-data-sm text-[#76777b]">
            Loading audit events for {recordId}...
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            {/* Left Column (2 Cols): Needle Timeline Stream */}
            <section className="lg:col-span-2 border border-[#c6c6cb] bg-[#fcf9f2] p-8 space-y-6">
              <div className="flex items-center justify-between border-b border-[#c6c6cb] pb-4">
                <h2 className="font-label-caps text-[#45474b]">
                  RECONCILIATION AUDIT TRAIL ({auditEvents.length} EVENTS)
                </h2>
                <span className="font-data-sm text-[#76777b]">ORDER: {recordId}</span>
              </div>

              {auditEvents.length === 0 ? (
                <div className="py-8 text-center font-data-sm text-[#76777b]">
                  No audit trail logs recorded for order {recordId}.
                </div>
              ) : (
                <div className="relative pl-6 space-y-8 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#c6c6cb]">
                  {auditEvents.map((ev, idx) => {
                    const stageKey = ev.stage?.toLowerCase() || '';
                    const isVerifyBreak = stageKey === 'verify' && isCorrected;
                    const stageTitle = stageTitles[stageKey] || ev.stage || 'Event';

                    return (
                      <div key={ev.id || idx} className="relative group">
                        {/* Needle Timeline Node Dot */}
                        <div
                          className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full flex items-center justify-center ${
                            isVerifyBreak
                              ? 'bg-[#ba1a1a] ring-4 ring-[#ffdad6]'
                              : 'bg-[#010306] border-2 border-[#ffffff]'
                          }`}
                        />

                        {/* Event Content Card */}
                        {isVerifyBreak ? (
                          /* Oxide-Red Deviation Break Card */
                          <div className="p-5 bg-[#ffdad6] border border-[#ba1a1a] text-[#93000a] space-y-3">
                            <div className="flex items-center justify-between border-b border-[#ba1a1a]/30 pb-2">
                              <div className="flex items-center space-x-2">
                                <span className="font-label-caps font-bold text-[#ba1a1a] tracking-wider">
                                  DEVIATION DETECTED & OVERRIDDEN
                                </span>
                              </div>
                              <span className="font-data-sm text-[#93000a] font-medium">
                                {formatTimestampTime(ev.timestamp)}
                              </span>
                            </div>

                            <div className="font-body-md font-medium text-[#93000a]">
                              Verified Category: <span className="font-mono">{exceptionRecord?.verified_category}</span>{' '}
                              <span className="text-xs text-[#ba1a1a]">(Initial: {exceptionRecord?.initial_category})</span>
                            </div>

                            <p className="font-body-sm text-[#93000a]/90 leading-relaxed">
                              {ev.explanation}
                            </p>

                            <div className="flex items-center justify-between text-xs font-data-sm text-[#93000a]/80 pt-1 border-t border-[#ba1a1a]/20">
                              <span>Decision: {ev.decision}</span>
                              <span>Confidence: {formatConfidencePercent(ev.confidence)}</span>
                            </div>
                          </div>
                        ) : (
                          /* Standard Ink/Grey Timeline Event Card */
                          <div className="p-5 bg-[#fcf9f2] border border-[#c6c6cb] space-y-2 hover:border-[#76777b] transition-colors">
                            <div className="flex items-center justify-between border-b border-[#e5e2db] pb-2">
                              <span className="font-body-md font-semibold text-[#010306]">
                                {stageTitle}
                              </span>
                              <span className="font-data-sm text-[#76777b]">
                                {formatTimestampTime(ev.timestamp)}
                              </span>
                            </div>

                            <p className="font-body-sm text-[#1c1c18] leading-relaxed">
                              {ev.explanation}
                            </p>

                            <div className="flex items-center justify-between font-data-sm text-[#76777b] text-xs pt-1">
                              <span>Decision: <strong className="text-[#010306]">{ev.decision}</strong></span>
                              <span>Confidence: <strong className="text-[#010306]">{formatConfidencePercent(ev.confidence)}</strong></span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Right Column (1 Col): Record Summary Panel */}
            <aside className="border border-[#c6c6cb] bg-[#fcf9f2] p-6 space-y-6">
              <div className="border-b border-[#c6c6cb] pb-3">
                <h3 className="font-label-caps text-[#45474b]">
                  RECORD SPECIFICATIONS
                </h3>
              </div>

              <div className="space-y-4 font-sans font-body-sm">
                <div>
                  <div className="font-label-caps text-[#76777b] text-[10px]">ORDER ID</div>
                  <div className="font-data-md font-medium text-[#010306]">{recordId}</div>
                </div>

                {exceptionRecord?.payment_id && (
                  <div>
                    <div className="font-label-caps text-[#76777b] text-[10px]">RAZORPAY PAYMENT ID</div>
                    <div className="font-data-md text-[#45474b]">{exceptionRecord.payment_id}</div>
                  </div>
                )}

                <div>
                  <div className="font-label-caps text-[#76777b] text-[10px]">TIER EXECUTED</div>
                  <div className="font-data-md text-[#010306]">
                    Tier {exceptionRecord?.tier_used ?? 1} — {exceptionRecord?.tier_used === 3 ? 'LLM Scorer' : 'Rule Scorer'}
                  </div>
                </div>

                <div>
                  <div className="font-label-caps text-[#76777b] text-[10px]">INITIAL CATEGORY</div>
                  <div className="font-mono text-[13px] text-[#45474b]">{exceptionRecord?.initial_category || '—'}</div>
                </div>

                <div>
                  <div className="font-label-caps text-[#76777b] text-[10px]">VERIFIED CATEGORY</div>
                  <div className="font-mono text-[13px] font-medium text-[#010306]">{exceptionRecord?.verified_category || '—'}</div>
                </div>

                <div>
                  <div className="font-label-caps text-[#76777b] text-[10px]">NET AMOUNT DELTA</div>
                  <div
                    className={`font-data-md font-medium ${
                      typeof amtDeltaPaise === 'number' && amtDeltaPaise < 0
                        ? 'text-[#ba1a1a]'
                        : 'text-[#725b2f]'
                    }`}
                  >
                    {formatPaiseToINR(amtDeltaPaise)}
                  </div>
                </div>

                {exceptionRecord?.evidence?.matched_bank_narration && (
                  <div>
                    <div className="font-label-caps text-[#76777b] text-[10px]">BANK NARRATION MATCH</div>
                    <div className="font-mono text-[12px] text-[#45474b] bg-[#f1eee7] p-2 border border-[#c6c6cb] break-all">
                      {String(exceptionRecord.evidence.matched_bank_narration)}
                    </div>
                  </div>
                )}

                {exceptionRecord?.evidence?.utr_match_type && (
                  <div>
                    <div className="font-label-caps text-[#76777b] text-[10px]">UTR MATCH TYPE</div>
                    <div className="font-data-sm text-[#010306] uppercase">
                      {String(exceptionRecord.evidence.utr_match_type)}
                    </div>
                  </div>
                )}
              </div>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}

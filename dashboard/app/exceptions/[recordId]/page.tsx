import { getAuditTrail } from '@/lib/api';
import Link from 'next/link';

interface PageProps {
  params: Promise<{
    recordId: string;
  }>;
}

export default async function RecordAuditPage({ params }: PageProps) {
  const { recordId } = await params;
  let auditData = null;
  let errorMsg = null;

  try {
    auditData = await getAuditTrail(recordId);
  } catch (err: unknown) {
    errorMsg = err instanceof Error ? err.message : String(err);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/exceptions"
            className="text-xs text-emerald-400 hover:underline mb-1 inline-block"
          >
            ← Back to Exceptions
          </Link>
          <h2 className="text-xl font-bold text-slate-100 font-mono">
            Audit Trail: {recordId}
          </h2>
        </div>
        {auditData && (
          <span className="text-xs px-2.5 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded font-mono">
            {auditData.total_events} Event(s) Recorded
          </span>
        )}
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-950/50 border border-red-800 text-red-300 rounded-lg text-sm">
          Failed to fetch audit trail for {recordId}: {errorMsg}
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-300">
          GET /audit/{recordId} Response
        </h3>
        <pre className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs overflow-x-auto text-emerald-400 max-h-[650px]">
          {auditData ? JSON.stringify(auditData, null, 2) : 'Loading or error...'}
        </pre>
      </div>
    </div>
  );
}

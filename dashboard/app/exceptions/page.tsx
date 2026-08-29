import { getExceptions } from '@/lib/api';
import Link from 'next/link';

export default async function ExceptionsPage() {
  let exceptionsData = null;
  let errorMsg = null;

  try {
    exceptionsData = await getExceptions();
  } catch (err: unknown) {
    errorMsg = err instanceof Error ? err.message : String(err);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100">
          Exceptions — Raw Array Dump ({exceptionsData?.total_exceptions || 0} Records)
        </h2>
        <div className="text-xs text-slate-400">
          Click any Order ID to view dynamic audit trail (`/exceptions/[recordId]`)
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-950/50 border border-red-800 text-red-300 rounded-lg text-sm">
          Failed to fetch exceptions: {errorMsg}
        </div>
      )}

      {exceptionsData && (
        <div className="flex flex-wrap gap-2 py-2">
          {exceptionsData.exceptions.map((ex) => (
            <Link
              key={ex.order_id}
              href={`/exceptions/${ex.order_id}`}
              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs transition-colors font-mono"
            >
              {ex.order_id}
            </Link>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-300">GET /exceptions Response</h3>
        <pre className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs overflow-x-auto text-emerald-400 max-h-[600px]">
          {exceptionsData ? JSON.stringify(exceptionsData, null, 2) : 'Loading or error...'}
        </pre>
      </div>
    </div>
  );
}

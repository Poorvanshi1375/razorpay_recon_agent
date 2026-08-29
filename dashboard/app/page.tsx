import { getResults, getExceptions } from '@/lib/api';

export default async function OverviewPage() {
  let resultsData = null;
  let exceptionsData = null;
  let errorMsg = null;

  try {
    resultsData = await getResults();
    exceptionsData = await getExceptions();
  } catch (err: unknown) {
    errorMsg = err instanceof Error ? err.message : String(err);
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-100">Overview — Raw JSON Contract Dump</h2>

      {errorMsg && (
        <div className="p-4 bg-red-950/50 border border-red-800 text-red-300 rounded-lg text-sm">
          Failed to fetch from backend: {errorMsg}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-300">GET /results</h3>
          <pre className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs overflow-x-auto text-emerald-400 max-h-[600px]">
            {resultsData ? JSON.stringify(resultsData, null, 2) : 'Loading or error...'}
          </pre>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-300">GET /exceptions</h3>
          <pre className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs overflow-x-auto text-emerald-400 max-h-[600px]">
            {exceptionsData ? JSON.stringify(exceptionsData, null, 2) : 'Loading or error...'}
          </pre>
        </div>
      </div>
    </div>
  );
}

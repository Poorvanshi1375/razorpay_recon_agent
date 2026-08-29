'use client';

import { useState } from 'react';
import { askQuestion } from '@/lib/api';
import { AskResponse } from '@/lib/types';

export default function AskPage() {
  const [question, setQuestion] = useState("Why didn't ORD-1061 match cleanly?");
  const [recordId, setRecordId] = useState('ORD-1061');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await askQuestion(question, recordId.trim() || undefined);
      setResponse(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-100">
        Settlement Q&A — Interactive Form & Raw POST Response Dump
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4 bg-slate-900 p-4 rounded-lg border border-slate-800">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Question
          </label>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Why didn't ORD-1061 match cleanly?"
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Order ID / Record ID (Optional)
          </label>
          <input
            type="text"
            value={recordId}
            onChange={(e) => setRecordId(e.target.value)}
            placeholder="e.g. ORD-1061"
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white font-medium text-sm rounded transition-colors"
        >
          {loading ? 'Executing POST /ask ...' : 'Submit POST /ask Request'}
        </button>
      </form>

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 text-red-300 rounded-lg text-sm">
          API Error: {error}
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-300">POST /ask Raw JSON Response Dump</h3>
        <pre className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs overflow-x-auto text-emerald-400 min-h-[200px]">
          {response ? JSON.stringify(response, null, 2) : loading ? 'Fetching from backend...' : 'Submit a question above to see the raw POST /ask response dump.'}
        </pre>
      </div>
    </div>
  );
}

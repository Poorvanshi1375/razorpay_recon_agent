import {
  RootStatusResponse,
  ResultsResponse,
  ExceptionsResponse,
  AuditTrailResponse,
  AskResponse,
  ReconcileRunResponse,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`API error ${response.status} fetching ${endpoint}`);
  }

  return response.json() as Promise<T>;
}

export async function getRootStatus(): Promise<RootStatusResponse> {
  return fetchAPI<RootStatusResponse>('/');
}

export async function getResults(): Promise<ResultsResponse> {
  return fetchAPI<ResultsResponse>('/results');
}

export async function getExceptions(): Promise<ExceptionsResponse> {
  return fetchAPI<ExceptionsResponse>('/exceptions');
}

export async function getAuditTrail(recordId: string): Promise<AuditTrailResponse> {
  return fetchAPI<AuditTrailResponse>(`/audit/${encodeURIComponent(recordId)}`);
}

export async function askQuestion(question: string, recordId?: string): Promise<AskResponse> {
  return fetchAPI<AskResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ question, record_id: recordId || null }),
  });
}

export async function runReconciliation(): Promise<ReconcileRunResponse> {
  return fetchAPI<ReconcileRunResponse>('/reconcile/run', {
    method: 'POST',
  });
}

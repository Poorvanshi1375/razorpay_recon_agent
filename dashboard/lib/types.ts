/**
 * TypeScript type definitions for Razorpay Multi-Source Reconciliation Agent API.
 * Derived directly from captured live API JSON responses.
 */

export interface RootStatusResponse {
  status: string;
  service: string;
  version: string;
  routes: string[];
}

export interface SummaryData {
  total_records: number;
  clean_matches: number;
  exceptions_classified: number;
  verified_resolved: number;
  needs_review: number;
  match_rate_percent: number;
}

export interface ReconcileRunResponse {
  status: string;
  message: string;
  run_id?: string;
  summary: SummaryData;
}

export interface ResultsResponse {
  status: string;
  summary: SummaryData;
}

export interface ExceptionEvidence {
  date_delta_days?: number;
  amount_delta_paise?: number;
  gross_amount_delta_paise?: number;
  utr_match_type?: string;
  is_batch?: boolean;
  is_duplicate?: boolean;
  reason?: string;
  matched_bank_amount?: number;
  matched_bank_narration?: string;
  [key: string]: unknown;
}

export interface ExceptionRecord {
  order_id: string;
  payment_id: string;
  tier_used: number;
  initial_category: string;
  verified_category: string;
  verifier_agreement: 'agreed' | 'corrected';
  status: string;
  verifier_confidence: number;
  verifier_reasoning: string;
  explanation: string;
  evidence: ExceptionEvidence;
}

export interface ExceptionsResponse {
  status: string;
  total_exceptions: number;
  exceptions: ExceptionRecord[];
}

export interface AuditEvent {
  id: number;
  run_id?: string;
  timestamp: string;
  stage: string;
  record_id: string;
  decision: string;
  confidence: number;
  explanation: string;
  evidence: Record<string, unknown>;
}

export interface AuditTrailResponse {
  status: string;
  record_id: string;
  run_id?: string;
  total_events: number;
  audit_events: AuditEvent[];
  message?: string;
}

export interface AskRequest {
  question: string;
  record_id?: string;
}

export interface AskResponse {
  status: string;
  question: string;
  record_id: string | null;
  answer: string;
  grounded_sources_count: number;
  detail?: string;
}

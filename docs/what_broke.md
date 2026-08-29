# Engineering Retrospective — What Broke & How We Fixed It

This document logs real engineering incidents, failure cases, and architectural fixes encountered during the development of the **AI Finance Controller — Multi-Source Reconciliation Agent**, as mandated by `AGENTS.md`.

---

## 1. Phase 1: Real-Sample Rounding Drift

* **What Broke**: Real-sample fee and tax amounts were initially recomputed using a generic `2% fee + 18% GST` formula instead of preserving the exact fee and tax values captured from the real Razorpay settlement data. This introduced a small rounding drift (1-2 paise) in real-sample-derived records, causing clean matches to fail tolerance checks.
* **How Caught**: Comparing synthetic and real-sample-derived records against exact ledger net settlement calculations.
* **How Fixed**: Updated `data/create_orders.py` and `data/generator.py` to read and use `real["fee"]` and `real["tax"]` values directly from captured Razorpay sample records without recomputing them.

---

## 2. Phase 2: Audit Trail Stage Coverage Gap

* **What Broke**: `engine/matcher.py` did not invoke `log_event()`, leaving the `ingest` and `match` stages unrecorded. As a result, the SQLite audit trail was missing 2 of the 5 pipeline stages for every record.
* **How Caught**: Direct SQL inspection of `data/audit_log.db` revealed that only `classify`, `verify`, and `rule_promotion` stages were present in audit event rows.
* **How Fixed**: Instrumenting `engine/matcher.py` with explicit `log_event()` calls for `ingest` and `match` stages across all ingestion and matching code paths, verified against both clean-matched and exception records.

---

## 3. Phase 3 & 6: Evaluation Integrity Bug in Ground Truth Scoring

* **What Broke**: The original `eval/score_against_ground_truth.py` used a permissive `CATEGORY_ALIAS` mapping that allowed `unresolved` or `matched` to be scored as "correct" predictions for categories specifically designed to test the opposite (e.g., exception cases that must not auto-match).
* **How Caught**: Manual review of the scoring logic prior to trusting initial 100% accuracy claims.
* **How Fixed**: Replaced the alias mapping with a strict binary evaluation model: clean records must be matched by the Phase 2 matcher, while exception records must not auto-match, must be resolved by the verifier, and must strictly equal their expected canonical target category (`garbled_utr` $\rightarrow$ `reference_formatting_issue`, `unexplained_bank_amount_discrepancy` $\rightarrow$ `amount_mismatch`).

---

## 4. Phase 3 & 5: Silent Gemini Model Deprecation & Error Masking

* **What Broke**: Candidate models `gemini-2.5-flash` and `gemini-1.5-flash` returned HTTP 404 errors due to API deprecation, but the candidate loop silently swallowed these errors and fell through without logging warnings. Furthermore, when all models failed, only the error of the *last* model attempted was retained, masking the root cause of primary model failure.
* **How Caught**: Inspecting API error payloads during Tier 3 LLM execution.
* **How Fixed**: Added explicit console and audit log warnings whenever a candidate model fails, and updated the fallback loop in `engine/classifier/llm_tier.py` and `engine/verifier.py` to aggregate all per-model error strings into `model_errors`.

---

## 5. Phase 5: Verifier Category Validation Gap

* **What Broke**: `engine/verifier.py` accepted any category string returned in the LLM's JSON response without validating it against `ALLOWED_CATEGORIES`, unlike `engine/classifier/llm_tier.py` which strictly enforced category validation.
* **How Caught**: Architecture consistency audit between the classifier and verifier modules.
* **How Fixed**: Added `ALLOWED_CATEGORIES` validation to `engine/verifier.py`, falling back to `unresolved` if an unknown category is returned, and created a unit test (`test_verifier_invalid_category_fallback`) to verify the safeguard.

---

## 6. Phase 6: `/ask` Q&A Endpoint Grounding and Status Gaps

* **What Broke**: 
  1. When a user submitted a plain-text question (e.g., `"Why didn't ORD-1057 settle?"`) without populating `payload.record_id`, the `/ask` endpoint fetched the first 15 unrelated database rows (`ORD-1000`) as grounding context while answering as if specific to `ORD-1057`.
  2. The endpoint exception handler returned `status="success"` even when the underlying Gemini call threw an unhandled exception.
* **How Caught**: Testing the `/ask` endpoint with plain-text queries and simulated network/API exceptions.
* **How Fixed**: Added regex order ID extraction (`r"\bORD-\d+\b"`) in `api/main.py` to extract embedded order IDs when `payload.record_id` is missing, and updated exception handling to return `status="error"`.

---

## 7. External Constraint: Gemini Daily Free-Tier Quota Exhaustion & Resolution

* **What Broke**: Primary model `gemini-3.6-flash` failed with HTTP 429 (`RESOURCE_EXHAUSTED: Quota exceeded for limit: 20 requests/day`) during intensive end-to-end testing.
* **Constraint & Policy**: `AGENTS.md` strictly prohibits paid subscriptions or adding credit cards. A free solution was required.
* **How Fixed**: Investigated available models via `ListModels` API (which does not consume generation quota), identified `gemini-3.5-flash-lite`, and confirmed via a single direct `generateContent` call that it possesses an independent daily quota. Updated `CANDIDATE_MODELS` order in `llm_tier.py` and `verifier.py` to `["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite"]`, restoring 100% pipeline accuracy.

---

## 8. Process Lesson: Deferred Git Commit Batching

* **What Broke**: A substantial portion of project work (Phases 3 through 6, unit tests, and multiple bug fixes) remained uncommitted in the working tree across an extended development window.
* **How Caught**: A `git status` check revealed over 10 untracked and modified files across multiple components.
* **Lesson**: Features and bug fixes should be committed in small, logical units immediately after verification to maintain a clean revision history and prevent monolithic commit batching.

---

## 9. Phase 5 & Spec Correction: Verifier Agreement vs. Resolution Status Discrepancy

* **What Broke**: `PROJECT_SPEC.md` originally stated that agreement between initial classification and verifier resulted in `status="resolved"`, whereas disagreement resulted in `status="needs_review"`. In practice, the Gemini verifier agent successfully resolved and corrected misclassifications (such as `ORD-1061`, where initial `reference_formatting_issue` was corrected to `amount_mismatch`) with high confidence (0.95) while writing `status="resolved"`. As a result, `needs_review` had never fired on real dataset records (remaining at 0), while verifier corrections were happening silently without explicit UI visibility.
* **How Caught**: Deep verification audit of the `GET /exceptions` payload and `engine/verifier.py` logic.
* **How Fixed**: Corrected `PROJECT_SPEC.md` §10 to clarify that `status` reflects verifier execution validity and confidence (reserving `needs_review` for verifier failure modes like API errors or invalid categories), and introduced an additive `verifier_agreement` attribute (`"agreed"` vs. `"corrected"`) across `engine/verifier.py`, `api/main.py`, and `dashboard/lib/types.ts` to make second-pass verifier corrections explicitly visible.


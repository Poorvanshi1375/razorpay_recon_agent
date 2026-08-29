# Project Spec: AI Finance Controller — Multi-Source Reconciliation Agent

Razorpay AI Internship Challenge — Track 4 (AI Finance Controller)

## 1. One-liner

An agent that reconciles a merchant's sales ledger, Razorpay settlement report, and bank statement, resolves discrepancies through a tiered classification pipeline, self-verifies its own uncertain calls, and reports an honest match rate against a held-out answer key — with a full audit trail and a natural-language Q&A layer on top.

## 2. Problem statement

A merchant's three financial records — what they think they sold (ledger), what Razorpay says it settled (settlement report), and what actually landed in the bank (bank statement) — routinely disagree. Fees get deducted, settlements get batched, timing lags a few days, and occasionally something genuinely goes wrong (a missing credit, a duplicate, an orphaned entry). Today this gets reconciled by hand. This project automates it, and — critically — measures itself honestly rather than just claiming to work.

## 3. Hard constraints

- **Zero paid tools/subscriptions anywhere in the stack.** Every tool listed below is free-tier or fully local.
- **Public repo.** No secrets, no `.env`, no proprietary code from any prior employer committed at any point.
- **Architecture is inspired by, not copied from, a prior internship codebase.** Patterns (tiered classification, structured audit logging, human/agent review workbench) are reimplemented clean-room for this domain. No company-specific logic, branding, or literal source files are reused.
- **No cybersecurity/cryptography angle.** Explicitly out of scope by the builder's preference — the audit trail is a structured, queryable event log, not a cryptographic signing system.
- **Honest measurement over impressive-looking demos.** A ground-truth answer key is written before the matching engine exists, is never read by any agent code, and is the only thing match-rate/accuracy numbers are allowed to be computed against.

## 4. Track 4 bar (what "done" has to satisfy)

- Closes a real finance-ops loop across a 50+ record synthetic batch.
- Reports match rate.
- Reports an honest exception list — not a cherry-picked success case.
- Throughput + measured accuracy, not just "it works on this one example."

## 5. Architecture overview

```
[Ledger] [Settlement Report] [Bank Statement]
        \        |         /
         v       v        v
         Phase 2: Matching Engine
      (deterministic join + fuzzy match + tolerance bands)
                  |
        matched ----------- unmatched/ambiguous
                              |
                  Phase 3: Exception Classifier
                (Rules -> Heuristic Score -> LLM)
                              |
                  low-confidence classifications
                              |
                  Phase 5: Verifier Agent
              (independent second-pass review)
                              |
                     resolved / needs-review
                              |
        --------------------------------------------
        |                                          |
  Phase 4: Audit Trail                    Phase 6: API + Dashboard
  (structured event log,                  (FastAPI + Next.js,
   SQLite, queryable)                      match rate, exceptions,
                                            Settlement Q&A chat)
```

## 6. Phase 1 — Data Layer

### 6.1 Sourcing strategy (hybrid)

- Capture 8–10 **real** Razorpay test-mode Payment objects (via actual test checkout) to lock in an authentic schema: real `payment_id` format, real `fee`/`tax` calculation.
- Generate the remaining 40+ records **synthetically**, using that captured schema as the template, so that specific problem cases can be deliberately and reproducibly planted.

### 6.2 Schemas

**Ledger record**
```
order_id: str            # internal, e.g. ORD-10234
razorpay_payment_id: str # pay_XXXXXXXXXXXXXX
order_amount: int        # in paise, matches Razorpay convention
order_date: date
status: enum[paid, refunded, partially_refunded]
```

**Settlement record**
```
settlement_id: str       # setl_XXXXXXXXXXXXXX
payment_ids: list[str]   # one settlement can batch multiple payments
amount: int               # gross, paise
fees: int
tax: int
net_settled_amount: int  # amount - fees - tax
utr: str
settled_at: date
```

**Bank statement record**
```
txn_date: date
credited_amount: int
narration: str   # UTR embedded in realistic, messy bank-style text
                  # e.g. "NEFT-RZP2547891UTR-RAZORPAY SOFTWARE PVT L"
```

### 6.3 Deliberately planted cases (target mix across ~55 records)

| Category | Count | Description |
|---|---|---|
| Clean match | ~35 | All three sources agree, fee/tax correctly deducted |
| Batch aggregation | ~5 | One bank credit = sum of several settlement entries |
| Normal T+2/T+3 lag | ~5 | Date gap that must resolve as *expected*, not flagged |
| Refund pair | ~2 | Paired negative entry across ledger/settlement/bank |
| Garbled UTR | ~3 | UTR truncated/reformatted in bank narration — requires fuzzy match |
| Rounding noise | ~2 | Paisa-level difference, should auto-tolerate |
| Missing bank credit (genuine problem) | ~2 | Settlement shows "settled," no matching bank entry |
| Duplicate settlement (genuine problem) | ~1 | Same payment settled twice |
| Orphan ledger entry (genuine problem) | ~1 | Ledger shows paid, no matching Razorpay payment exists at all |

### 6.4 Ground-truth answer key

A separate file (`ground_truth.json`), authored manually alongside data generation, mapping every record to its true category. **Never read by matching or classification code.** Used only by the evaluation script at the end, to compute honest match rate, precision/recall, and false-positive cost.

### 6.5 Tools

`pandas`, `Faker`, official `razorpay` Python SDK — all free.

## 7. Phase 2 — Matching Engine

1. Deterministic join: `ledger.razorpay_payment_id` → `settlement.payment_ids` → `settlement.utr` → UTR extracted from `bank.narration` via fuzzy string matching (`rapidfuzz`, not exact match, since narrations are messy by design).
2. Amount checks with tolerance bands, mirroring balance-continuity-auditing logic: `ledger.order_amount == settlement.amount` (gross); `settlement.net_settled_amount ≈ bank.credited_amount` within a small paise tolerance.
3. Batch handling: before declaring a bank credit unmatched, check whether it equals the sum of multiple settlement entries.
4. Every record exits this phase with a `match_status` (`matched` / `ambiguous` / `unmatched`) and a `confidence` score (0–1), which feeds Phase 3.

## 8. Phase 3 — Exception Classification

Tiered pipeline, same shape as Rules → ML → LLM, applied to *why a record didn't cleanly match* rather than *what category an expense is*:

- **Tier 1 — Rules.** Deterministic checks: delta ≈ typical fee % → `fee_deduction`; date delta within settlement cycle → `normal_lag`; negative amount matching a prior positive → `refund`.
- **Tier 2 — Heuristic confidence score**, *not a trained ML model.* With only ~55 records there isn't enough data to meaningfully train anything — this tier is a weighted-feature scorer (amount delta %, date delta, string similarity) and should be labeled honestly as such in the README, not oversold as "ML."
- **Tier 3 — LLM.** Genuinely ambiguous cases get a natural-language explanation from a local Ollama model (or Gemini free tier as fallback).
- **Rule promotion loop.** If the LLM repeatedly explains the same pattern the same way (same delta range, same reasoning), promote it into a Tier 1 rule so future runs skip the LLM call — with a minimum-sample-size guard before promoting, to avoid a bad rule getting promoted off one lucky case.

## 9. Phase 4 — Audit Trail

Structured, staged event log: every ingest/match/classify/resolve step writes a record with stage, record ID, decision, confidence, and evidence. **Storage: SQLite** (built into Python, zero setup, zero external account) — deliberately not a hosted database, to avoid an unnecessary free-tier dependency. Exposed via a query endpoint so any decision is traceable after the fact.

## 10. Phase 5 — Verifier Agent (self-verifying loop)

Low-confidence Tier 3 classifications get a second, independent LLM pass — given the first classification and explicitly asked to find fault with it, not confirm it. The record's `status` reflects whether the verifier produced a successful, valid, confident classification (either via Tier 1 auto-approval or a successful Gemini verifier call), NOT whether it agreed with the initial classification; `needs_review` is reserved for verifier failure modes (API errors across candidates, invalid category returned, or missing API key with a non-zero amount delta). Separately, an additive `verifier_agreement` attribute ("agreed" / "corrected") records whether the final verified category matched the initial classification, and does not influence `status`. This provides an explicit, transparent audit of verifier corrections while keeping resolved exceptions fully classified.

## 11. Phase 6 — API + Dashboard

- **FastAPI backend:** `/reconcile/run`, `/results`, `/exceptions`, `/audit/{record_id}`, `/ask` (Settlement Q&A — answers are generated from the actual retrieved audit trail/match data for that record, not free-floating from model memory).
- **Next.js dashboard:** match-rate summary, exceptions table with drill-down into each record's reasoning, and a chat box for the Q&A layer.
- Runs locally for development and demo recording — no paid hosting required.

## 12. Repo structure

```
razorpay-recon-agent/
├── AGENTS.md
├── PROJECT_SPEC.md
├── README.md
├── .env.example
├── .gitignore
├── data/
│   ├── generator.py
│   ├── real_samples/
│   ├── ledger.csv
│   ├── settlement.csv
│   ├── bank_statement.csv
│   └── ground_truth.json
├── engine/
│   ├── matcher.py
│   ├── classifier/
│   │   ├── rules.py
│   │   ├── heuristic_score.py
│   │   └── llm_tier.py
│   ├── verifier.py
│   └── audit_log.py
├── api/
│   └── main.py
├── dashboard/
│   └── (Next.js app)
├── eval/
│   └── score_against_ground_truth.py
└── docs/
    └── what_broke.md
```

## 13. Evaluation methodology

`eval/score_against_ground_truth.py` runs after the full pipeline, compares final classifications against `ground_truth.json`, and reports: match rate, precision/recall per category, false-positive cost (a genuinely-fine record wrongly flagged as a problem), and a plain list of anything still unresolved. This output is what goes in the README and the video — not a hand-picked success run.

## 14. Explicitly out of scope

- Any cryptographic signing/verification of the audit trail.
- Any claim of a "trained ML model" — Tier 2 is a heuristic scorer, call it that.
- Paid hosting, paid LLM APIs, paid databases.
- Copying literal code, branding, or company-specific business logic from any prior employer's codebase.

## 15. Video narrative candidates ("what broke")

Track honestly in `docs/what_broke.md` as you go. Likely genuine candidates: matching tolerance thresholds too tight/loose on first pass; batch-aggregation logic coincidentally summing unrelated settlements into a false match; rule-promotion promoting a bad rule before the minimum-sample-size guard was added. Use whichever actually happened — don't manufacture one.

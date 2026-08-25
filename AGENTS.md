# AGENTS.md — Standing instructions for this workspace

Read `PROJECT_SPEC.md` in full before starting any task — it has the complete architecture, schemas, and phase-by-phase plan. This file is the short version: hard constraints every agent must follow, every session, no exceptions.

## Project

Multi-source reconciliation agent (ledger vs. Razorpay settlement report vs. bank statement) for the Razorpay AI Internship Challenge, Track 4 (AI Finance Controller).

## Absolute constraints

- **No paid tools, APIs, or subscriptions, anywhere.** If a task seems to need one, stop and flag it instead of proceeding — a free alternative should exist (see PROJECT_SPEC.md §"Tools").
- **SQLite only** for the audit log — never introduce a hosted/cloud database.
- **Never write to, read from, or reference `.env` in any commit.** Use `.env.example` with placeholder values only.
- **`ground_truth.json` is read-only and only ever touched by `eval/score_against_ground_truth.py`.** No matching, classification, or verifier code may read it, directly or indirectly. This is the honesty mechanism for the whole project — treat it as sacred.
- **No cryptographic signing, hashing-for-tamper-proofing, or any security/crypto framing anywhere in this project.** Out of scope by explicit choice.
- **Never claim "trained ML model."** The Tier 2 classification step is a heuristic weighted-feature scorer with ~55 records of data — call it that, in code comments, docstrings, and the README.
- **No code, branding, or business logic copied from any prior employer's codebase.** Architectural patterns may be reimplemented from scratch; literal source must not be reused.

## Coding standards

- Python: type hints required on public functions, PEP 8, docstrings on every module-level function.
- All amounts handled as integers in paise, never floats, to avoid rounding bugs in the reconciliation logic itself (separate from the rounding-noise test cases, which are deliberate).
- Every pipeline stage (ingest/match/classify/verify/resolve) must write to the audit log before returning — no silent steps.
- New features get their own file — no growing `main.py` into a monolith.

## Where things go

Full repo layout is in `PROJECT_SPEC.md` §12. Generator scripts in `data/`, core logic in `engine/`, API in `api/`, dashboard in `dashboard/`, evaluation in `eval/`.

## When stuck

Log the failure and the fix in `docs/what_broke.md` as it happens — this is direct input to the submission video, not an afterthought to write later.

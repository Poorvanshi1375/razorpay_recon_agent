"""
Tier 3 Exception Classifier: Gemini LLM Integration.

Uses the Gemini Flash API (via google-genai SDK) to classify complex or ambiguous
reconciliation exceptions that Tier 1 (Rules) and Tier 2 (Heuristic Scorer) could not resolve.

Constrained to JSON output with fixed categories.
Wrapped in try/except to prevent network or API failures from crashing execution.
Does NOT read ground_truth.json (per AGENTS.md).
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

ALLOWED_CATEGORIES = {
    "duplicate_settlement",
    "missing_bank_credit",
    "orphan_ledger_entry",
    "reference_formatting_issue",
    "amount_mismatch",
    "likely_explainable",
    "unresolved",
}

# Model fallback sequence for robust API execution (gemini-3.6-flash is primary active free-tier model)
CANDIDATE_MODELS: List[str] = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]


def classify_tier3_llm(
    order_id: str,
    payment_id: str,
    settlement_id: Optional[str],
    evidence: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Tuple[str, float, str]:
    """
    Classify an unresolved record using Gemini Flash LLM.

    Returns:
        (category, confidence, explanation) tuple.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return (
            "unresolved",
            0.0,
            "Tier 3 LLM skipped: GEMINI_API_KEY is not set in environment or .env file.",
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        prompt = f"""
You are a senior finance reconciliation AI controller analyzing a payment anomaly.

Record Details:
- Order ID: {order_id}
- Payment ID: {payment_id}
- Settlement ID: {settlement_id}
- Evidence: {json.dumps(evidence, indent=2)}

Task:
Analyze why this record failed clean reconciliation and classify it into EXACTLY ONE category from this list:
- duplicate_settlement
- missing_bank_credit
- orphan_ledger_entry
- reference_formatting_issue
- amount_mismatch
- likely_explainable
- unresolved

Output Requirement:
Return ONLY a valid JSON object formatted as follows:
{{
  "category": "category_name",
  "confidence": 0.85,
  "explanation": "One sentence plain-English explanation."
}}
"""

        response_text = None
        model_errors = []
        primary_model = CANDIDATE_MODELS[0]

        for model_name in CANDIDATE_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                if response and response.text:
                    if model_name != primary_model:
                        print(
                            f"[WARNING] Tier 3 Model Fallback Triggered: Primary model '{primary_model}' unavailable. "
                            f"Successfully fell back to '{model_name}'."
                        )
                    response_text = response.text
                    break
            except Exception as mod_err:
                print(
                    f"[WARNING] Tier 3 Model '{model_name}' unavailable ({mod_err}). "
                    f"Attempting fallback..."
                )
                model_errors.append(f"{model_name}: {mod_err}")
                continue

        if not response_text:
            err_summary = "; ".join(model_errors) if model_errors else "No response generated."
            return (
                "unresolved",
                0.0,
                f"Tier 3 LLM failed: All candidate models failed. Errors: {err_summary}",
            )

        data = json.loads(response_text)
        category = data.get("category", "unresolved")
        confidence = float(data.get("confidence", 0.5))
        explanation = str(data.get("explanation", "No explanation provided by LLM."))

        if category not in ALLOWED_CATEGORIES:
            category = "unresolved"

        # Clamp confidence to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))

        return (category, confidence, explanation)

    except Exception as exc:
        return (
            "unresolved",
            0.0,
            f"Tier 3 LLM classification exception caught: {str(exc)}",
        )

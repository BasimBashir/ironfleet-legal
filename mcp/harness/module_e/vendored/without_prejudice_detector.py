"""
without_prejudice_detector.py — BN-03
Category C / IRON skill.
Classifies correspondence as WP, WPSATC, or OPEN per Evidence Act 2006 s57.
All confidence arithmetic uses decimal.Decimal.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from typing import Any

# ── Injection detection patterns ──────────────────────────────────────────

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"disregard\s+your\s+(previous|instructions|rules)", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you", re.IGNORECASE),
]

# ── Settlement context indicators (Evidence Act s57) ─────────────────────

_SETTLEMENT_INDICATORS = [
    re.compile(r"in\s+full\s+and\s+final\s+settlement", re.IGNORECASE),
    re.compile(r"in\s+settlement\s+of", re.IGNORECASE),
    re.compile(r"offer\s+to\s+settle", re.IGNORECASE),
    re.compile(r"settlement\s+offer", re.IGNORECASE),
    re.compile(r"without\s+admission", re.IGNORECASE),
    re.compile(r"in\s+compromise\s+of", re.IGNORECASE),
    re.compile(r"calderbank\s+offer", re.IGNORECASE),
    re.compile(r"open\s+to\s+accept", re.IGNORECASE),
    re.compile(r"costs\s+consequences", re.IGNORECASE),
    re.compile(r"to\s+avoid\s+(the\s+cost|litigation|proceedings)", re.IGNORECASE),
]

# ── WP / WPSATC header patterns ───────────────────────────────────────────

_WPSATC_HEADER = re.compile(
    r"^\s*WITHOUT\s+PREJUDICE\s+SAVE\s+AS\s+TO\s+COSTS\b",
    re.IGNORECASE | re.MULTILINE,
)
_WP_HEADER = re.compile(
    r"^\s*WITHOUT\s+PREJUDICE\b(?!\s+SAVE\s+AS\s+TO\s+COSTS)",
    re.IGNORECASE | re.MULTILINE,
)
_PRIVILEGED_CONFIDENTIAL = re.compile(
    r"^\s*PRIVILEGED\s+AND\s+CONFIDENTIAL\b",
    re.IGNORECASE | re.MULTILINE,
)
_LEGALLY_PRIVILEGED_HEADER = re.compile(
    r"^\s*LEGALLY\s+PRIVILEGED\b",
    re.IGNORECASE | re.MULTILINE,
)

# ── WPSATC body patterns ──────────────────────────────────────────────────

_CALDERBANK_BODY = re.compile(r"\bcalderbank\b", re.IGNORECASE)
_WPSATC_BODY = re.compile(
    r"\bwithout\s+prejudice\s+save\s+as\s+to\s+costs\b",
    re.IGNORECASE,
)

# ── WP body pattern ───────────────────────────────────────────────────────

_WP_BODY = re.compile(r"\bwithout\s+prejudice\b", re.IGNORECASE)


# ── Confidence calculation ────────────────────────────────────────────────

def calculate_confidence(signals: list[tuple[str, float, float]]) -> float:
    """
    Weighted signal confidence per Annex §3.2.1.
    All arithmetic uses Decimal. float() only at output boundary.
    """
    if not signals:
        raise ValueError("calculate_confidence: empty signal list")
    total_weight = sum(Decimal(str(w)) for _, w, _ in signals)
    if total_weight == 0:
        raise ValueError("calculate_confidence: weights sum to zero")
    weighted_sum = sum(
        Decimal(str(w)) * Decimal(str(s)) for _, w, s in signals
    )
    clamped = min(Decimal("1.0"), max(Decimal("0.0"), weighted_sum / total_weight))
    return float(clamped)


# ── Input hash ────────────────────────────────────────────────────────────

def _input_hash(payload: dict[str, Any]) -> str:
    safe = {k: v for k, v in payload.items() if k != "content"}
    safe["content_len"] = len(payload.get("content", ""))
    serialised = json.dumps(safe, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


# ── Injection check ───────────────────────────────────────────────────────

def _has_injection(text: str) -> bool:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ── Settlement context score ──────────────────────────────────────────────

def _settlement_score(text: str) -> float:
    """0.0-1.0 proportional to number of settlement indicators found, capped at 1.0."""
    count = sum(1 for p in _SETTLEMENT_INDICATORS if p.search(text))
    return float(min(Decimal(str(count)) / Decimal("3"), Decimal("1.0")))


# ── Main entry point ──────────────────────────────────────────────────────

def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Classify correspondence as WP, WPSATC, or OPEN.

    Args:
        payload: {
            content:           str   — required
            subject_line:      str   — optional
            trust_tier:        str   — required (T0-T3)
            operator_override: bool  — required for T0
            case_state:        dict  — optional, read only
        }

    Returns:
        Standard Iron Fleet result dict.
    """
    ih = _input_hash(payload)

    # ── Validate required fields ──────────────────────────────────────────
    for field in ("content", "trust_tier"):
        if field not in payload:
            return {
                "status": "ERROR",
                "result": None,
                "confidence": None,
                "flags": ["[MISSING-REQUIRED-FIELD]"],
                "error": {
                    "type": "MALFORMED_INPUT",
                    "message": f"Required field '{field}' missing",
                    "retry_recommended": False,
                    "input_hash": ih,
                },
            }

    content = payload["content"]
    subject = payload.get("subject_line", "")
    trust_tier = payload["trust_tier"]
    operator_override = payload.get("operator_override", False)

    # ── T0 gate ───────────────────────────────────────────────────────────
    if trust_tier == "T0" and not operator_override:
        return {
            "status": "ERROR",
            "result": None,
            "confidence": None,
            "flags": ["[T0-CONTENT-BLOCKED]"],
            "error": {
                "type": "MALFORMED_INPUT",
                "message": "T0 content requires operator_override: true",
                "retry_recommended": False,
                "input_hash": ih,
            },
        }

    # ── Injection check ───────────────────────────────────────────────────
    combined = f"{subject}\n{content}"
    if _has_injection(combined):
        return {
            "status": "FLAGGED",
            "result": None,
            "confidence": 0.0,
            "flags": ["[INJECTION-ATTEMPT-DETECTED — MANUAL REVIEW]"],
            "trust_tier": trust_tier,
        }

    # ── Marker detection ──────────────────────────────────────────────────
    wpsatc_header = bool(_WPSATC_HEADER.search(content))
    wp_header = bool(_WP_HEADER.search(content))
    priv_conf_header = bool(_PRIVILEGED_CONFIDENTIAL.search(content))
    legally_priv_header = bool(_LEGALLY_PRIVILEGED_HEADER.search(content))

    wpsatc_body = bool(_WPSATC_BODY.search(content)) or bool(_CALDERBANK_BODY.search(content))

    subject_has_wp = bool(_WP_HEADER.search(subject)) or bool(_WP_BODY.search(subject))
    subject_has_wpsatc = (
        bool(_WPSATC_HEADER.search(subject))
        or bool(_WPSATC_BODY.search(subject))
        or bool(_CALDERBANK_BODY.search(subject))
    )

    settlement_ctx_score = _settlement_score(combined)
    has_settlement_context = settlement_ctx_score > 0.0

    # ── Determine signals — header takes priority over body ───────────────
    has_wp_header = wp_header or priv_conf_header or legally_priv_header
    has_wpsatc_header = wpsatc_header
    # Only count body-only WPSATC if no header already found
    has_wpsatc_body_only = wpsatc_body and not has_wpsatc_header and not has_wp_header

    has_wp_signal = has_wp_header
    has_wpsatc_signal = has_wpsatc_header or has_wpsatc_body_only

    # ── Conflict check ────────────────────────────────────────────────────
    if has_wp_signal and has_wpsatc_signal:
        return {
            "status": "FLAGGED",
            "result": None,
            "confidence": 0.45,
            "flags": ["[WP-STATUS-UNCERTAIN — MANUAL REVIEW]"],
            "trust_tier": trust_tier,
        }

    # ── Settlement context without markers ────────────────────────────────
    if has_settlement_context and not has_wp_signal and not has_wpsatc_signal:
        return {
            "status": "FLAGGED",
            "result": None,
            "confidence": round(settlement_ctx_score * 0.6, 2),
            "flags": ["[WP-STATUS-UNCERTAIN — MANUAL REVIEW]"],
            "trust_tier": trust_tier,
        }

    # ── Classify ──────────────────────────────────────────────────────────
    if has_wpsatc_signal:
        wp_status = "WPSATC"
        is_header = has_wpsatc_header
        triggering_phrase = (
            "WITHOUT PREJUDICE SAVE AS TO COSTS" if has_wpsatc_header
            else "Calderbank / without prejudice save as to costs (body)"
        )
        marker_type = "header" if is_header else "body"
        explicit_score = 1.0 if is_header else 0.7
        subject_score = 1.0 if subject_has_wpsatc else (0.5 if subject_has_wp else 0.0)
        reasoning = (
            f"WPSATC marker detected ({'header' if is_header else 'body'}). "
            f"Triggering phrase: '{triggering_phrase}'. "
            f"Admissible on costs only per NZ case law. Classification: WPSATC."
        )

    elif has_wp_signal:
        wp_status = "WP"
        is_header = True
        if wp_header:
            triggering_phrase = "WITHOUT PREJUDICE"
        elif priv_conf_header:
            triggering_phrase = "PRIVILEGED AND CONFIDENTIAL"
        else:
            triggering_phrase = "LEGALLY PRIVILEGED"
        marker_type = "header"
        explicit_score = 1.0
        subject_score = 1.0 if subject_has_wp else 0.0
        reasoning = (
            f"WP header marker detected: '{triggering_phrase}'. "
            f"Evidence Act s57 protection applies — inadmissible on merits. "
            f"Classification: WP."
        )

    else:
        wp_status = "OPEN"
        is_header = False
        triggering_phrase = None
        marker_type = "absent"
        explicit_score = 0.0
        subject_score = 0.0
        reasoning = (
            "No WP or WPSATC markers found in header or body. "
            "No settlement-context indicators found. "
            "Absence-of-marker rule applies. "
            "Classification: OPEN — pending confidence threshold check."
        )

    # ── Calculate confidence ──────────────────────────────────────────────
    context_score = 1.0 if wp_status != "OPEN" else 0.95

    if is_header:
        # Header marker is dominant standalone legal evidence.
        # Corroborating signals default to neutral 0.5 when absent —
        # absence of subject/settlement markers does not reduce confidence
        # when a header marker is present.
        signals = [
            ("explicit_marker_found",    0.70, explicit_score),
            ("marker_in_subject_line",   0.10, subject_score if subject_score > 0 else 0.5),
            ("settlement_context_check", 0.10, settlement_ctx_score if settlement_ctx_score > 0 else 0.5),
            ("context_consistent",       0.10, context_score),
        ]

    elif wp_status == "OPEN":
        # OPEN classification — absence of ALL privilege signals is the
        # positive evidence. Invert scoring: 1.0 for each signal absent.
        signals = [
            ("explicit_marker_absent",    0.50, 1.0 - explicit_score),
            ("subject_marker_absent",     0.20, 1.0 if subject_score == 0.0 else 0.0),
            ("settlement_context_absent", 0.20, 1.0 if settlement_ctx_score == 0.0 else 0.0),
            ("context_consistent",        0.10, context_score),
        ]

    else:
        # Body-only WPSATC — corroborating signals neutral when absent
        signals = [
            ("explicit_marker_found",    0.50, explicit_score),
            ("marker_in_subject_line",   0.20, subject_score if subject_score > 0 else 0.5),
            ("settlement_context_check", 0.20, settlement_ctx_score if settlement_ctx_score > 0 else 0.5),
            ("context_consistent",       0.10, context_score),
        ]

    confidence = calculate_confidence(signals)

    # ── OPEN confidence gate — must be >= 0.90 ────────────────────────────
    # Per Annex §3.2 privilege override: a false OPEN at < 0.90 is
    # irreversible once it enters the disclosure pipeline.
    if wp_status == "OPEN" and confidence < 0.90:
        return {
            "status": "FLAGGED",
            "result": None,
            "confidence": round(confidence, 2),
            "flags": ["[WP-STATUS-UNCERTAIN — MANUAL REVIEW]"],
            "trust_tier": trust_tier,
        }

    # ── Apply threshold table (Annex §3.2) ───────────────────────────────
    flags = []
    if 0.75 <= confidence < 0.90:
        flags.append("[REVIEW-RECOMMENDED]")

    if confidence < 0.50:
        return {
            "status": "FLAGGED",
            "result": None,
            "confidence": round(confidence, 2),
            "flags": ["[ESCALATE-TO-HUMAN — CLASSIFICATION-REQUIRES-MANUAL-REVIEW]"],
            "escalation": {
                "recommended_mode": "HUMAN",
                "reason": "Confidence below 0.50 — requires practitioner review",
                "retain_input": True,
            },
            "trust_tier": trust_tier,
        }

    if confidence < 0.75:
        return {
            "status": "FLAGGED",
            "result": None,
            "confidence": round(confidence, 2),
            "flags": ["[WP-STATUS-UNCERTAIN — MANUAL REVIEW]"],
            "trust_tier": trust_tier,
        }

    return {
        "status": "SUCCESS",
        "result": {
            "wp_status": wp_status,
            "confidence": round(confidence, 2),
            "triggering_phrase": triggering_phrase,
            "marker_type": marker_type,
            "reasoning_chain": reasoning,
        },
        "confidence": round(confidence, 2),
        "flags": flags,
        "trust_tier": trust_tier,
    }
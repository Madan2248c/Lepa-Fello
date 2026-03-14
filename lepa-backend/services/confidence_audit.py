"""
Confidence audit trail service.

Produces a structured audit of how confident the system is in each
output field, which sources contributed, and how many evidence items
were collected. Designed to be transparent and demo-friendly.
"""

from typing import Any
from schemas.output_models import AnalyzeResponse


def build_confidence_audit(result: AnalyzeResponse) -> dict[str, Any]:
    """
    Build a field-level confidence audit for an analysis result.

    Returns a structured dict with:
    - overall_confidence: top-level score
    - field_confidence: per-field confidence values
    - evidence_counts: how many items were found per section
    - source_quality: classification of each source type used
    - audit_notes: human-readable notes explaining the confidence

    Args:
        result: Completed AnalyzeResponse from the pipeline.

    Returns:
        Audit dict suitable for API response or logging.
    """
    field_confidence: dict[str, float] = {}
    evidence_counts: dict[str, int] = {}
    audit_notes: list[str] = []

    # ── Company profile fields ────────────────────────────────────────────────
    field_confidence["account_name"] = 0.9 if result.account_name else 0.0
    field_confidence["domain"] = 0.95 if result.domain else 0.0
    field_confidence["industry"] = 0.8 if result.industry else 0.0
    field_confidence["headquarters"] = 0.75 if result.headquarters else 0.0
    field_confidence["company_size"] = 0.75 if result.company_size else 0.0
    field_confidence["founded_year"] = 0.7 if result.founded_year else 0.0
    field_confidence["business_description"] = 0.8 if result.business_description else 0.0

    # ── Persona ───────────────────────────────────────────────────────────────
    field_confidence["persona"] = result.persona.confidence
    if result.input_type == "company_seed":
        audit_notes.append("Persona confidence is 0 — no visitor behavior data for company seed input.")
    elif result.persona.confidence < 0.4:
        audit_notes.append("Persona confidence is low — limited browsing signals available.")

    # ── Intent ────────────────────────────────────────────────────────────────
    field_confidence["intent"] = min(1.0, result.intent.score / 10)
    if result.input_type == "company_seed":
        audit_notes.append("Intent score is a default estimate — no visitor behavior data.")

    # ── Phase 2 enrichment ────────────────────────────────────────────────────
    tech_count = len(result.technology_stack)
    signal_count = len(result.business_signals)
    leadership_count = len(result.leadership)

    evidence_counts["technology_stack"] = tech_count
    evidence_counts["business_signals"] = signal_count
    evidence_counts["leadership"] = leadership_count
    evidence_counts["source_links"] = len(result.source_links)
    evidence_counts["key_signals_observed"] = len(result.key_signals_observed)

    if tech_count > 0:
        avg_tech_conf = sum(t.confidence for t in result.technology_stack) / tech_count
        field_confidence["technology_stack"] = round(avg_tech_conf, 2)
        builtwith_count = sum(1 for t in result.technology_stack if t.source == "builtwith")
        if builtwith_count > 0:
            audit_notes.append(f"Tech stack: {builtwith_count}/{tech_count} technologies verified via BuiltWith API.")
        else:
            audit_notes.append("Tech stack: detected via page scan only (lower confidence).")
    else:
        field_confidence["technology_stack"] = 0.0
        audit_notes.append("Tech stack: no technologies detected.")

    if signal_count > 0:
        avg_sig_conf = sum(s.confidence for s in result.business_signals) / signal_count
        field_confidence["business_signals"] = round(avg_sig_conf, 2)
        dated = sum(1 for s in result.business_signals if s.published_at)
        audit_notes.append(f"Business signals: {signal_count} found, {dated} with publication dates.")
    else:
        field_confidence["business_signals"] = 0.0
        audit_notes.append("Business signals: none found in public sources.")

    if leadership_count > 0:
        avg_lead_conf = sum(c.confidence for c in result.leadership) / leadership_count
        field_confidence["leadership"] = round(avg_lead_conf, 2)
        audit_notes.append(f"Leadership: {leadership_count} contacts identified from public sources.")
    else:
        field_confidence["leadership"] = 0.0
        audit_notes.append("Leadership: no contacts found in public sources.")

    # ── Source quality classification ─────────────────────────────────────────
    source_quality: dict[str, str] = {}
    for link in result.source_links:
        if "linkedin.com" in link:
            source_quality[link] = "high — official LinkedIn profile"
        elif "apollo.io" in link or "apollo" in link:
            source_quality[link] = "high — Apollo.io enrichment API"
        elif result.domain and result.domain in link:
            source_quality[link] = "high — official company website"
        else:
            source_quality[link] = "medium — third-party source"

    # ── Evidence from Phase 2 ─────────────────────────────────────────────────
    if result.evidence:
        evidence_counts["website_pages_scraped"] = len(result.evidence.website_pages)
        evidence_counts["news_articles_found"] = len(result.evidence.news_links)

    return {
        "overall_confidence": result.overall_confidence,
        "field_confidence": field_confidence,
        "evidence_counts": evidence_counts,
        "source_quality": source_quality,
        "audit_notes": audit_notes,
    }

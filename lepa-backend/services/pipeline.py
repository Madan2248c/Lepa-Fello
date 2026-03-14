"""
Main analysis pipeline orchestrating all services.

Phase 1: Input normalization → company resolution → research → persona/intent → summary/recommendations
Phase 2: Tech stack detection → business signals → leadership discovery → confidence scoring
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from schemas.input_models import VisitorSignalInput, CompanySeedInput
from schemas.output_models import (
    AnalyzeResponse,
    PersonaResult,
    EnrichmentEvidence,
)
from schemas.internal_models import CompanyCandidate, CompanyProfile

from services.normalize import normalize_visitor_input, normalize_company_input
from services.company_resolution import (
    resolve_company_from_visitor,
    resolve_company_from_seed,
)
from services.research_agent import research_company
from services.persona import infer_persona, extract_key_signals
from services.intent import score_intent, get_default_intent_for_company_seed
from services.summarizer import generate_ai_summary
from services.recommender import generate_recommendations
from services.tech_stack import detect_tech_stack
from services.business_signals import discover_business_signals
from services.leadership import discover_leadership
from services.confidence import (
    score_tech_stack_confidence,
    score_business_signals_confidence,
    score_leadership_confidence,
    calculate_enrichment_confidence,
)
from models.pipeline_run import PipelineRun
from services.history import persist_result, save_run

logger = logging.getLogger("lepa.pipeline")


async def run_visitor_pipeline(input_data: VisitorSignalInput) -> AnalyzeResponse:
    """
    Full analysis pipeline for visitor signal input.

    Phase 1 stages:
    1. Normalize input
    2. Resolve company from IP
    3. Research and enrich company
    4. Infer persona from browsing behavior
    5. Score buying intent
    6. Generate AI summary and recommendations

    Phase 2 stages (run concurrently after Phase 1):
    7. Detect technology stack
    8. Discover business signals
    9. Discover leadership contacts
    10. Score confidence across all enrichment fields
    """
    normalized = normalize_visitor_input(input_data)
    candidate = await resolve_company_from_visitor(normalized)

    profile: Optional[CompanyProfile] = None
    if candidate.name or candidate.domain:
        profile = await research_company(candidate)
    else:
        profile = CompanyProfile(
            name="Unknown Visitor",
            confidence=0.0,
            source_links=[],
        )

    persona = infer_persona(normalized)
    intent = score_intent(normalized)
    key_signals = extract_key_signals(normalized)

    ai_summary, recommendations, phase2_results = await asyncio.gather(
        generate_ai_summary(profile, persona, intent, key_signals),
        generate_recommendations(profile, persona, intent),
        _run_phase2_enrichment(profile, candidate),
    )

    tech_stack, business_signals, leadership, news_links = phase2_results

    overall_confidence = calculate_enrichment_confidence(
        profile=profile,
        tech_stack=tech_stack,
        business_signals=business_signals,
        leadership=leadership,
        candidate_confidence=candidate.confidence,
        persona_confidence=persona.confidence,
    )

    all_source_links = list(dict.fromkeys(profile.source_links + news_links))

    result = AnalyzeResponse(
        input_type="visitor_signal",
        input_id=input_data.visitor_id,
        account_name=profile.name if profile.name != "Unknown Visitor" else None,
        domain=profile.domain,
        industry=profile.industry,
        headquarters=profile.headquarters,
        company_size=profile.company_size,
        founded_year=profile.founded_year,
        business_description=profile.description,
        persona=persona,
        intent=intent,
        technology_stack=tech_stack,
        business_signals=business_signals,
        leadership=leadership,
        key_signals_observed=key_signals,
        ai_summary=ai_summary,
        recommended_sales_action=recommendations,
        overall_confidence=overall_confidence,
        source_links=all_source_links,
        evidence=EnrichmentEvidence(
            website_pages=profile.source_links,
            news_links=news_links,
            technology_sources=[t.source for t in tech_stack],
        ),
        generated_at=datetime.now(timezone.utc),
    )

    _persist_to_history(result, input_type="visitor_signal")
    return result


async def run_company_pipeline(input_data: CompanySeedInput) -> AnalyzeResponse:
    """
    Full analysis pipeline for company seed input.

    Phase 1 stages:
    1. Normalize input
    2. Create company candidate from seed
    3. Research and enrich company via Strands Agent
    4. Default persona (no behavior data)
    5. Default intent score
    6. Generate AI summary and recommendations

    Phase 2 stages (run concurrently after Phase 1):
    7. Detect technology stack
    8. Discover business signals
    9. Discover leadership contacts
    10. Score confidence across all enrichment fields
    """
    normalized = normalize_company_input(input_data)
    candidate = resolve_company_from_seed(normalized)
    profile = await research_company(candidate)

    persona = PersonaResult(
        label="Unknown",
        confidence=0.0,
        reasons=["No visitor behavior data available for company seed input"],
    )
    intent = get_default_intent_for_company_seed()

    key_signals = [f"Company submitted directly: {input_data.company_name}"]
    if input_data.partial_domain:
        key_signals.append(f"Domain hint provided: {input_data.partial_domain}")
    if profile.industry:
        key_signals.append(f"Industry identified: {profile.industry}")
    if profile.company_size:
        key_signals.append(f"Company size: {profile.company_size} employees")

    ai_summary, recommendations, phase2_results = await asyncio.gather(
        generate_ai_summary(profile, persona, intent, key_signals),
        generate_recommendations(profile, persona, intent),
        _run_phase2_enrichment(profile, candidate),
    )

    tech_stack, business_signals, leadership, news_links = phase2_results

    overall_confidence = calculate_enrichment_confidence(
        profile=profile,
        tech_stack=tech_stack,
        business_signals=business_signals,
        leadership=leadership,
        candidate_confidence=candidate.confidence,
        persona_confidence=0.0,
    )

    all_source_links = list(dict.fromkeys(profile.source_links + news_links))

    result = AnalyzeResponse(
        input_type="company_seed",
        input_id=input_data.company_name,
        account_name=profile.name,
        domain=profile.domain,
        industry=profile.industry,
        headquarters=profile.headquarters,
        company_size=profile.company_size,
        founded_year=profile.founded_year,
        business_description=profile.description,
        persona=persona,
        intent=intent,
        technology_stack=tech_stack,
        business_signals=business_signals,
        leadership=leadership,
        key_signals_observed=key_signals,
        ai_summary=ai_summary,
        recommended_sales_action=recommendations,
        overall_confidence=overall_confidence,
        source_links=all_source_links,
        evidence=EnrichmentEvidence(
            website_pages=profile.source_links,
            news_links=news_links,
            technology_sources=[t.source for t in tech_stack],
        ),
        generated_at=datetime.now(timezone.utc),
    )

    _persist_to_history(result, input_type="company_seed")
    return result


def _persist_to_history(result: AnalyzeResponse, input_type: str) -> None:
    """Persist a completed analysis result to the account history store."""
    try:
        run = PipelineRun(
            account_id="pending",
            input_type=input_type,  # type: ignore[arg-type]
        )
        run.start()
        run.add_event("enriched")
        run.add_event("scored")
        run.add_event("summarized")
        run.complete()
        persist_result(result, run)
    except Exception as e:
        logger.warning(f"Failed to persist result to history: {e}")


async def _run_phase2_enrichment(
    profile: CompanyProfile,
    candidate: CompanyCandidate,
) -> tuple:
    """
    Run all Phase 2 enrichment tasks concurrently.

    Returns:
        Tuple of (tech_stack, business_signals, leadership, news_links).
    """
    company_name = profile.name or candidate.name or ""
    domain = profile.domain or candidate.domain

    if not company_name or company_name in ("Unknown Company", "Unknown Visitor"):
        return [], [], [], []

    tech_task = detect_tech_stack(domain=domain)
    signals_task = discover_business_signals(
        company_name=company_name,
        domain=domain,
    )
    leadership_task = discover_leadership(
        company_name=company_name,
        domain=domain,
    )

    tech_stack_raw, (business_signals_raw, news_links), leadership_raw = await asyncio.gather(
        tech_task,
        signals_task,
        leadership_task,
    )

    tech_stack = score_tech_stack_confidence(tech_stack_raw)
    business_signals = score_business_signals_confidence(business_signals_raw)
    leadership = score_leadership_confidence(leadership_raw)

    return tech_stack, business_signals, leadership, news_links

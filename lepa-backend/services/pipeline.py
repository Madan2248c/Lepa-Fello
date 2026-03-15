"""
Main analysis pipeline orchestrating all services.

Phase 1: Input normalization → company resolution → research → persona/intent → summary/recommendations
Phase 2: Tech stack detection → business signals → leadership discovery → confidence scoring
Phase 3: Buying committee → trend velocity → outreach drafts → ICP fit → competitive context
Phase 4: Deep research via multi-agent system (optional, async)
"""

import asyncio
import logging
import time
import httpx
from datetime import datetime, timezone
from typing import Optional

from schemas.input_models import VisitorSignalInput, CompanySeedInput
from schemas.internal_models import CompanyCandidate, CompanyProfile
from schemas.output_models import (
    AnalyzeResponse,
    PersonaResult,
    EnrichmentEvidence,
    PipelineStep,
    BuyingCommitteeMember,
    TrendVelocity,
    OutreachDraft,
    IcpFitScore,
    CompetitiveContext,
)
from services.icp_profile import calculate_icp_fit_score

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
from services.buying_committee import build_buying_committee
from services.trend_velocity import detect_trend_velocity
from services.outreach_draft import generate_outreach_drafts
from services.icp_fit import score_icp_fit
from services.icp_profile import calculate_icp_fit_score
from services.competitive_context import discover_competitive_context
from models.pipeline_run import PipelineRun
from services.history import persist_result, save_run

logger = logging.getLogger("lepa.pipeline")


async def run_visitor_pipeline(input_data: VisitorSignalInput, tenant_id: str = "default") -> AnalyzeResponse:
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

    trace: list[PipelineStep] = []

    t0 = time.time()
    trace.append(PipelineStep(step="IP Resolution", source="IPInfo", status="success" if candidate.name else "partial", duration_ms=int((time.time()-t0)*1000), note=f"Resolved IP to {candidate.name or 'unknown'} (confidence: {candidate.confidence:.0%})"))

    profile: Optional[CompanyProfile] = None
    if candidate.name or candidate.domain:
        t1 = time.time()
        profile = await research_company(candidate)
        trace.append(PipelineStep(step="Company Research", source="Strands Agent (Bedrock Sonnet)", status="success" if profile.name else "partial", duration_ms=int((time.time()-t1)*1000), note=f"Resolved: {profile.name or 'unknown'}"))
    else:
        profile = CompanyProfile(name="Unknown Visitor", confidence=0.0, source_links=[])
        trace.append(PipelineStep(step="Company Research", source="Strands Agent", status="failed", note="No company identified from IP — visitor remains anonymous"))

    persona = infer_persona(normalized)
    intent = score_intent(normalized)
    key_signals = extract_key_signals(normalized)
    trace.append(PipelineStep(step="Persona & Intent", source="deterministic rules", status="success", note=f"Persona: {persona.label} ({persona.confidence:.0%}), Intent: {intent.score}/10 ({intent.stage})"))

    # Load business profile for personalized recommendations
    business_profile = None
    try:
        from clients.db_client import get_business_profile
        business_profile = await get_business_profile(tenant_id)
    except Exception:
        pass

    ai_summary, recommendations, phase2_results = await asyncio.gather(
        generate_ai_summary(profile, persona, intent, key_signals),
        generate_recommendations(profile, persona, intent, business_profile),
        _run_phase2_enrichment(profile, candidate, trace),
    )

    tech_stack, business_signals, leadership, news_links, prefetched_profiles = phase2_results

    # Phase 3: run advanced intelligence concurrently
    tech_names = [t.name for t in tech_stack]
    signal_types = [s.type for s in business_signals]
    signal_summaries = [s.summary for s in business_signals]

    t3 = time.time()
    buying_committee_raw, trend_velocity_raw, outreach_raw, competitive_raw = await asyncio.gather(
        build_buying_committee(leadership, enrich_with_linkedin=True, company_name=profile.name or "", industry=profile.industry or "", tenant_id=tenant_id, prefetched_profiles=prefetched_profiles),
        detect_trend_velocity(profile.name or "", profile.domain),
        generate_outreach_drafts(profile, persona, intent, key_signals, signal_summaries, tech_names, ai_summary),
        discover_competitive_context(profile.name or "", profile.domain, tech_names),
    )
    p3_ms = int((time.time()-t3)*1000)

    icp_raw = await score_icp_fit(profile, tech_stack, signal_types, icp_industries=input_data.icp_industries or [], icp_size_min=input_data.icp_size_min or 11, icp_size_max=input_data.icp_size_max or 5000)

    trace.append(PipelineStep(step="Buying Committee", source="ICP-prioritized + Apify LinkedIn", status="success" if buying_committee_raw else "partial", duration_ms=p3_ms, records_found=len(buying_committee_raw)))
    trace.append(PipelineStep(step="Trend Velocity", source="Exa (date-filtered)", status="success" if trend_velocity_raw.get("status") != "unknown" else "partial", duration_ms=p3_ms, note=f"{trend_velocity_raw.get('status','unknown')} — {trend_velocity_raw.get('velocity_ratio',0)}x"))
    trace.append(PipelineStep(step="Outreach Drafts", source="Bedrock Haiku", status="success" if outreach_raw.get("email_subject") else "failed", duration_ms=p3_ms))
    trace.append(PipelineStep(step="ICP Fit Scoring", source="deterministic (4-dimension)", status="success", note=f"{icp_raw['overall_score']}/100 — {icp_raw['tier']}"))
    trace.append(PipelineStep(step="Competitive Context", source="Exa + BuiltWith mapping", status="success" if competitive_raw.get("competitive_mentions") else "partial", duration_ms=p3_ms))

    overall_confidence = calculate_enrichment_confidence(
        profile=profile,
        tech_stack=tech_stack,
        business_signals=business_signals,
        leadership=leadership,
        candidate_confidence=candidate.confidence,
        persona_confidence=persona.confidence,
    )

    trace.append(PipelineStep(step="Confidence Scoring", source="weighted ensemble", status="success", note=f"Overall: {overall_confidence:.0%}"))

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
        buying_committee=[BuyingCommitteeMember(**m) for m in buying_committee_raw],
        trend_velocity=TrendVelocity(**trend_velocity_raw),
        outreach_draft=OutreachDraft(**outreach_raw),
        icp_fit=IcpFitScore(**icp_raw),
        competitive_context=CompetitiveContext(**competitive_raw),
        pipeline_trace=trace,
        generated_at=datetime.now(timezone.utc),
    )

    _persist_to_history(result, input_type="visitor_signal", tenant_id=tenant_id)
    await _persist_contacts(buying_committee_raw, profile, source_type="visitor", source_id=input_data.visitor_id, tenant_id=tenant_id)
    return result


async def run_company_pipeline(input_data: CompanySeedInput, tenant_id: str = "default") -> AnalyzeResponse:
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

    trace: list[PipelineStep] = []
    pipeline_start = time.time()

    t0 = time.time()
    profile = await research_company(candidate)
    trace.append(PipelineStep(step="Company Research", source="Strands Agent (Bedrock Sonnet)", status="success" if profile.name else "partial", duration_ms=int((time.time()-t0)*1000), note=f"Resolved: {profile.name or 'unknown'}, domain: {profile.domain or 'unknown'}"))

    persona = PersonaResult(
        label="Unknown",
        confidence=0.0,
        reasons=["No visitor behavior data available for company seed input"],
    )
    intent = get_default_intent_for_company_seed()
    trace.append(PipelineStep(step="Persona & Intent", source="deterministic", status="skipped", note="Company seed input — no visitor behavior to analyze"))

    key_signals = [f"Company submitted directly: {input_data.company_name}"]
    if input_data.partial_domain:
        key_signals.append(f"Domain hint provided: {input_data.partial_domain}")
    if profile.industry:
        key_signals.append(f"Industry identified: {profile.industry}")
    if profile.company_size:
        key_signals.append(f"Company size: {profile.company_size} employees")

    # Load business profile for personalized recommendations
    business_profile_2 = None
    try:
        from clients.db_client import get_business_profile
        business_profile_2 = await get_business_profile(tenant_id)
    except Exception:
        pass

    ai_summary, recommendations, phase2_results = await asyncio.gather(
        generate_ai_summary(profile, persona, intent, key_signals),
        generate_recommendations(profile, persona, intent, business_profile_2),
        _run_phase2_enrichment(profile, candidate, trace),
    )

    tech_stack, business_signals, leadership, news_links, prefetched_profiles = phase2_results

    # Phase 3: run advanced intelligence concurrently
    tech_names = [t.name for t in tech_stack]
    signal_types = [s.type for s in business_signals]
    signal_summaries = [s.summary for s in business_signals]
    top_contact_name = leadership[0].get("name", "") if leadership else ""

    t3 = time.time()
    buying_committee_raw, trend_velocity_raw, outreach_raw, competitive_raw = await asyncio.gather(
        build_buying_committee(leadership, enrich_with_linkedin=True, company_name=profile.name or "", industry=profile.industry or "", tenant_id=tenant_id, prefetched_profiles=prefetched_profiles),
        detect_trend_velocity(profile.name or "", profile.domain),
        generate_outreach_drafts(profile, persona, intent, key_signals, signal_summaries, tech_names, ai_summary, contact_name=top_contact_name),
        discover_competitive_context(profile.name or "", profile.domain, tech_names),
    )
    p3_ms = int((time.time()-t3)*1000)

    icp_raw = await score_icp_fit(profile, tech_stack, signal_types, icp_industries=input_data.icp_industries or [], icp_size_min=input_data.icp_size_min or 11, icp_size_max=input_data.icp_size_max or 5000)

    trace.append(PipelineStep(step="Buying Committee", source="deterministic + Apify LinkedIn", status="success" if buying_committee_raw else "partial", duration_ms=p3_ms, records_found=len(buying_committee_raw), note=f"{len(buying_committee_raw)} members classified" if buying_committee_raw else "No leadership data to classify"))
    trace.append(PipelineStep(step="Trend Velocity", source="Exa (date-filtered)", status="success" if trend_velocity_raw.get("status") != "unknown" else "partial", duration_ms=p3_ms, note=f"{trend_velocity_raw.get('status','unknown')} — {trend_velocity_raw.get('velocity_ratio',0)}x baseline"))
    trace.append(PipelineStep(step="Outreach Drafts", source="Bedrock Haiku", status="success" if outreach_raw.get("email_subject") else "failed", duration_ms=p3_ms, note="AI-generated cold email + LinkedIn message" if outreach_raw.get("email_subject") else "Generation failed — insufficient context"))
    trace.append(PipelineStep(step="ICP Fit Scoring", source="deterministic (4-dimension)", status="success", note=f"{icp_raw['overall_score']}/100 — {icp_raw['tier']}"))
    trace.append(PipelineStep(step="Competitive Context", source="Exa + BuiltWith mapping", status="success" if competitive_raw.get("competitive_mentions") else "partial", duration_ms=p3_ms, records_found=len(competitive_raw.get("competitive_mentions",[])), note=f"{len(competitive_raw.get('competitive_mentions',[]))} competitor mentions found"))

    overall_confidence = calculate_enrichment_confidence(
        profile=profile,
        tech_stack=tech_stack,
        business_signals=business_signals,
        leadership=leadership,
        candidate_confidence=candidate.confidence,
        persona_confidence=0.0,
    )

    trace.append(PipelineStep(step="Confidence Scoring", source="weighted ensemble", status="success", note=f"Overall: {overall_confidence:.0%} — weighted across {sum(1 for s in trace if s.status=='success')} successful enrichment sources"))

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
        buying_committee=[BuyingCommitteeMember(**m) for m in buying_committee_raw],
        trend_velocity=TrendVelocity(**trend_velocity_raw),
        outreach_draft=OutreachDraft(**outreach_raw),
        icp_fit=IcpFitScore(**icp_raw),
        competitive_context=CompetitiveContext(**competitive_raw),
        pipeline_trace=trace,
        generated_at=datetime.now(timezone.utc),
    )

    _persist_to_history(result, input_type="company_seed", tenant_id=tenant_id)
    await _persist_contacts(buying_committee_raw, profile, source_type="company", source_id=input_data.company_name, tenant_id=tenant_id)

    return result


def _persist_to_history(result: AnalyzeResponse, input_type: str, tenant_id: str = "default") -> None:
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
        persist_result(result, run, tenant_id=tenant_id)
    except Exception as e:
        logger.warning(f"Failed to persist result to history: {e}")


async def _persist_contacts(buying_committee: list[dict], profile: CompanyProfile, source_type: str, source_id: str, tenant_id: str) -> None:
    """Save buying committee members to contacts table."""
    if not buying_committee:
        return
    try:
        contacts = [
            {
                **m,
                "company_name": profile.name or "",
                "company_domain": profile.domain or "",
                "source_type": source_type,
                "source_id": source_id,
            }
            for m in buying_committee
        ]
        from clients.db_client import upsert_contacts
        await upsert_contacts(tenant_id, contacts)
    except Exception as e:
        logger.warning(f"Failed to persist contacts: {e}")


async def _run_phase2_enrichment(
    profile: CompanyProfile,
    candidate: CompanyCandidate,
    trace: list,
) -> tuple:
    """
    Run all Phase 2 enrichment tasks concurrently, recording trace steps.

    Returns:
        Tuple of (tech_stack, business_signals, leadership, news_links, prefetched_profiles).
    """
    company_name = profile.name or candidate.name or ""
    domain = profile.domain or candidate.domain

    if not company_name or company_name in ("Unknown Company", "Unknown Visitor"):
        trace.append(PipelineStep(step="Phase 2", source="pipeline", status="skipped", note="No company identified"))
        return [], [], [], []

    t0 = time.time()
    tech_task = detect_tech_stack(domain=domain)
    signals_task = discover_business_signals(company_name=company_name, domain=domain)
    leadership_task = discover_leadership(company_name=company_name, domain=domain)

    tech_stack_raw, (business_signals_raw, news_links), (leadership_raw, prefetched_profiles) = await asyncio.gather(
        tech_task, signals_task, leadership_task,
    )
    elapsed = int((time.time() - t0) * 1000)

    tech_stack = score_tech_stack_confidence(tech_stack_raw)
    business_signals = score_business_signals_confidence(business_signals_raw)
    leadership = score_leadership_confidence(leadership_raw)

    trace.append(PipelineStep(step="Tech Stack Detection", source="BuiltWith" if domain else "page_scan", status="success" if tech_stack else "failed", duration_ms=elapsed, records_found=len(tech_stack), note=f"{len(tech_stack)} technologies detected" if tech_stack else "No tech stack data — domain may block crawlers"))
    trace.append(PipelineStep(step="Business Signals", source="Exa", status="success" if business_signals else "partial", duration_ms=elapsed, records_found=len(business_signals), note=f"{len(business_signals)} signals found" if business_signals else "No public signals found — company may be pre-revenue or stealth"))
    trace.append(PipelineStep(step="Leadership Discovery", source="Exa+Apollo", status="success" if leadership else "partial", duration_ms=elapsed, records_found=len(leadership), note=f"{len(leadership)} decision-makers identified" if leadership else "No leadership data — limited public presence"))

    return tech_stack, business_signals, leadership, news_links, prefetched_profiles

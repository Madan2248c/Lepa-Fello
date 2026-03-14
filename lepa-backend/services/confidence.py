"""
Field-level confidence scoring for Phase 2 enrichment.

Confidence rules follow the principle:
  official company page > external API > weak text match > absent

Scores increase when multiple independent sources agree on the same value.
All scoring is transparent and rule-based — no black-box models.
"""

from typing import Optional

from schemas.output_models import (
    TechStackItem,
    BusinessSignal,
    LeadershipContact,
)
from schemas.internal_models import CompanyProfile


def score_profile_confidence(profile: CompanyProfile) -> float:
    """
    Score the overall confidence in a company profile.

    Weights:
    - Name present: +0.15
    - Domain present: +0.15
    - Industry present: +0.10
    - Description present: +0.10
    - HQ present: +0.10
    - Company size present: +0.10
    - Founded year present: +0.05
    - LinkedIn URL present: +0.10
    - Source links present: +0.10
    - Multiple source links: +0.05
    """
    score = 0.0

    if profile.name and profile.name not in ("Unknown Company", "Unknown Visitor"):
        score += 0.15
    if profile.domain:
        score += 0.15
    if profile.industry:
        score += 0.10
    if profile.description:
        score += 0.10
    if profile.headquarters:
        score += 0.10
    if profile.company_size:
        score += 0.10
    if profile.founded_year:
        score += 0.05
    if profile.linkedin_url:
        score += 0.10
    if profile.source_links:
        score += 0.10
        if len(profile.source_links) >= 2:
            score += 0.05

    return round(min(1.0, score), 2)


def score_tech_stack_confidence(
    items: list[TechStackItem],
) -> list[TechStackItem]:
    """
    Adjust confidence on tech stack items based on source quality.

    Rules:
    - builtwith source: base 0.9 (API-verified)
    - page_scan source: base 0.6 (pattern match only)
    - If same tech appears in both sources: boost to 0.95
    """
    builtwith_names = {i.name.lower() for i in items if i.source == "builtwith"}
    pagescan_names = {i.name.lower() for i in items if i.source == "page_scan"}
    both = builtwith_names & pagescan_names

    adjusted = []
    for item in items:
        conf = item.confidence
        if item.name.lower() in both:
            conf = 0.95
        elif item.source == "builtwith":
            conf = 0.9
        elif item.source == "page_scan":
            conf = 0.6
        adjusted.append(
            TechStackItem(
                category=item.category,
                name=item.name,
                confidence=round(conf, 2),
                source=item.source,
            )
        )

    return adjusted


def score_business_signals_confidence(
    signals: list[BusinessSignal],
) -> list[BusinessSignal]:
    """
    Adjust confidence on business signals.

    Rules:
    - Signal has a published date: +0.05
    - Signal has a source URL: base maintained
    - Signal has no source URL: -0.15
    - Funding signals get a slight boost (high-value, well-covered)
    """
    adjusted = []
    for signal in signals:
        conf = signal.confidence

        if signal.published_at:
            conf = min(0.95, conf + 0.05)
        if not signal.source_url:
            conf = max(0.1, conf - 0.15)
        if signal.type == "funding":
            conf = min(0.95, conf + 0.05)

        adjusted.append(
            BusinessSignal(
                type=signal.type,
                summary=signal.summary,
                published_at=signal.published_at,
                source_url=signal.source_url,
                confidence=round(conf, 2),
            )
        )

    return adjusted


def score_leadership_confidence(
    contacts: list[LeadershipContact],
) -> list[LeadershipContact]:
    """
    Adjust confidence on leadership contacts.

    Rules:
    - Contact has a source URL: base maintained
    - Contact has no source URL (from LinkedIn employees list): -0.05
    - Full name (first + last): base maintained
    - Single-word name: -0.20
    """
    adjusted = []
    for contact in contacts:
        conf = contact.confidence

        if not contact.source_url:
            conf = max(0.1, conf - 0.05)

        name_parts = contact.name.strip().split()
        if len(name_parts) < 2:
            conf = max(0.1, conf - 0.20)

        adjusted.append(
            LeadershipContact(
                name=contact.name,
                title=contact.title,
                source_url=contact.source_url,
                confidence=round(conf, 2),
            )
        )

    return adjusted


def calculate_enrichment_confidence(
    profile: CompanyProfile,
    tech_stack: list[TechStackItem],
    business_signals: list[BusinessSignal],
    leadership: list[LeadershipContact],
    candidate_confidence: float,
    persona_confidence: float,
) -> float:
    """
    Calculate the overall confidence for a fully enriched Phase 2 response.

    Weights:
    - Profile quality (40%): Foundation of the analysis
    - Candidate resolution (25%): How well we identified the company
    - Persona inference (15%): Behavioral understanding
    - Phase 2 enrichment bonus (20%): Tech stack, signals, leadership depth
    """
    profile_conf = score_profile_confidence(profile)

    enrichment_bonus = 0.0
    if tech_stack:
        enrichment_bonus += 0.07
    if business_signals:
        enrichment_bonus += 0.07
    if leadership:
        enrichment_bonus += 0.06
    enrichment_bonus = min(0.20, enrichment_bonus)

    score = (
        profile_conf * 0.40
        + candidate_confidence * 0.25
        + persona_confidence * 0.15
        + enrichment_bonus
    )

    return round(min(1.0, max(0.0, score)), 2)

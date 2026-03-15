"""
ICP (Ideal Customer Profile) fit scoring service.

Scores how well an account matches a configurable ICP definition using LLM reasoning.
Default ICP targets: B2B SaaS companies, 50-5000 employees, using modern tech stack.

Returns a 0-100 score with dimension breakdown and fit tier.
"""

import logging
from typing import Optional

from clients.bedrock_client import invoke_claude
from schemas.output_models import TechStackItem
from schemas.internal_models import CompanyProfile

logger = logging.getLogger("lepa.icp_fit")

ICP_PROMPT = """You are a B2B sales intelligence expert. Score how well this company matches an Ideal Customer Profile (ICP) for a sales outreach campaign.

ICP TARGETS:
- Industries: software, saas, technology, fintech, healthtech, edtech, ecommerce, marketplace, b2b, enterprise software, cloud, cybersecurity, data, analytics, ai, machine learning
- Company sizes: 11-50, 51-200, 201-500, 501-1000, 1001-5000 employees (sweet spot)
- Tech stack: modern tools (CRM, marketing automation, analytics, devtools) = positive signal
- Business signals: hiring, funding, expansion, product_launch = positive momentum

INPUT:
Company: {company_name}
Industry: {industry}
Size: {company_size}
HQ: {headquarters}
Founded: {founded_year}
Tech Stack: {tech_stack}
Business Signals: {business_signals}

OUTPUT FORMAT (JSON only):
{{
  "overall_score": 0-100,
  "tier": "Strong Fit" | "Good Fit" | "Partial Fit" | "Poor Fit",
  "dimension_scores": {{
    "industry_fit": 0-100,
    "size_fit": 0-100,
    "tech_stack_fit": 0-100,
    "momentum_fit": 0-100
  }},
  "fit_reasons": ["1-2 sentence explanation for each dimension that scores well"],
  "gap_reasons": ["1-2 sentence explanation for each dimension that scores poorly"]
}}"""


async def score_icp_fit(
    profile: CompanyProfile,
    tech_stack: list[TechStackItem],
    business_signal_types: list[str],
    icp_industries: list[str] = None,
    icp_size_min: int = 11,
    icp_size_max: int = 5000,
) -> dict:
    """
    Score account fit against ICP definition using LLM reasoning.

    Dimensions (each 0-100, weighted):
    - Industry fit (30%)
    - Company size fit (25%)
    - Tech stack signals (25%)
    - Business momentum signals (20%)

    Args:
        icp_industries: Target industries from user config
        icp_size_min: Minimum company size from user config
        icp_size_max: Maximum company size from user config

    Returns:
        Dict with overall_score (0-100), tier, dimension_scores, fit_reasons, gap_reasons
    """
    # Build prompt with company context
    tech_names = ", ".join([t.name for t in tech_stack[:10]]) if tech_stack else "None detected"
    signal_types = ", ".join(business_signal_types) if business_signal_types else "None detected"

    # Build ICP context for the prompt
    icp_context = f"Target Industries: {', '.join(icp_industries or []) or 'Any'} | Size Range: {icp_size_min}-{icp_size_max} employees"

    prompt = ICP_PROMPT.format(
        company_name=profile.name or "Unknown",
        industry=profile.industry or "Unknown",
        company_size=profile.company_size or "Unknown",
        headquarters=profile.headquarters or "Unknown",
        founded_year=profile.founded_year or "Unknown",
        tech_stack=tech_names,
        business_signals=signal_types,
    )

    try:
        response = await invoke_claude(prompt=prompt, model="haiku", max_tokens=800)
        return _parse_icp_response(response)
    except Exception as e:
        logger.warning(f"LLM ICP scoring failed: {e}, falling back to deterministic")
        return _fallback_score_icp(profile, tech_stack, business_signal_types)


def _parse_icp_response(response: str) -> dict:
    """Parse the LLM ICP response."""
    import json
    import re
    result = {
        "overall_score": 50,
        "tier": "Partial Fit",
        "dimension_scores": {"industry_fit": 50, "size_fit": 50, "tech_stack_fit": 50, "momentum_fit": 50},
        "fit_reasons": [],
        "gap_reasons": [],
    }

    try:
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if "overall_score" in data:
                result["overall_score"] = max(0, min(100, int(data["overall_score"])))
            if "tier" in data:
                result["tier"] = data["tier"]
            if "dimension_scores" in data:
                result["dimension_scores"].update(data["dimension_scores"])
            if "fit_reasons" in data:
                result["fit_reasons"] = data["fit_reasons"][:4]
            if "gap_reasons" in data:
                result["gap_reasons"] = data["gap_reasons"][:4]
    except Exception:
        pass

    return result


def _fallback_score_icp(
    profile: CompanyProfile,
    tech_stack: list[TechStackItem],
    business_signal_types: list[str],
) -> dict:
    """Fallback deterministic scoring if LLM fails."""
    # Default ICP definition
    target_industries = [
        "software", "saas", "technology", "fintech", "healthtech", "edtech",
        "ecommerce", "marketplace", "b2b", "enterprise software", "cloud",
        "cybersecurity", "data", "analytics", "ai", "machine learning",
    ]
    target_sizes = ["11-50", "51-200", "201-500", "501-1000", "1001-5000"]
    positive_tech = ["crm", "marketing_automation", "analytics", "devtools"]
    positive_signals = ["hiring", "funding", "expansion", "product_launch"]

    # Industry score
    ind = 100 if profile.industry and any(k in profile.industry.lower() for k in target_industries) else 25

    # Size score
    sz = 90 if profile.company_size and any(s in profile.company_size for s in target_sizes) else 35

    # Tech score
    tech_cats = [t.category for t in tech_stack]
    pos_hits = [c for c in tech_cats if c in positive_tech]
    tech = min(100, 40 + len(pos_hits) * 20)

    # Signal score
    sig_hits = [s for s in business_signal_types if s in positive_signals]
    sig = min(100, 30 + len(sig_hits) * 25)

    overall = round(ind * 0.30 + sz * 0.25 + tech * 0.25 + sig * 0.20)
    tier = "Strong Fit" if overall >= 80 else "Good Fit" if overall >= 60 else "Partial Fit" if overall >= 40 else "Poor Fit"

    return {
        "overall_score": overall,
        "tier": tier,
        "dimension_scores": {"industry_fit": ind, "size_fit": sz, "tech_stack_fit": tech, "momentum_fit": sig},
        "fit_reasons": [],
        "gap_reasons": [],
    }

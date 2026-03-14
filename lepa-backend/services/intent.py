from typing import Literal

from schemas.internal_models import NormalizedAccountInput
from schemas.output_models import IntentResult


IntentStage = Literal["Awareness", "Research", "Evaluation", "Decision"]


INTENT_WEIGHTS = {
    "pricing_visit": 3.0,
    "case_studies_visit": 1.5,
    "demo_request_page": 2.5,
    "multiple_visits_week": 2.0,
    "long_session": 2.0,
    "multiple_product_pages": 1.5,
    "docs_visit": 1.0,
    "blog_only_penalty": -1.0,
    "referral_linkedin": 0.5,
    "referral_google": 0.3,
}


def score_intent(normalized_input: NormalizedAccountInput) -> IntentResult:
    """
    Calculate buying intent score from visitor behavior.
    
    Uses weighted heuristics based on known high-intent signals.
    Returns a score 0-10 and maps to funnel stage.
    """
    ctx = normalized_input.visitor_context
    pages = ctx.pages_visited
    
    score = 0.0
    reasons = []

    pages_lower = [p.lower() for p in pages]

    if any("/pricing" in p or "/plans" in p for p in pages_lower):
        score += INTENT_WEIGHTS["pricing_visit"]
        reasons.append("Visited pricing page (+3.0)")

    if any("/demo" in p or "/trial" in p or "/contact-sales" in p for p in pages_lower):
        score += INTENT_WEIGHTS["demo_request_page"]
        reasons.append("Visited demo/trial request page (+2.5)")

    if any("/case-stud" in p or "/customers" in p or "/testimonial" in p for p in pages_lower):
        score += INTENT_WEIGHTS["case_studies_visit"]
        reasons.append("Viewed case studies/testimonials (+1.5)")

    if any("/docs" in p or "/api" in p or "/documentation" in p for p in pages_lower):
        score += INTENT_WEIGHTS["docs_visit"]
        reasons.append("Explored documentation (+1.0)")

    product_pages = sum(
        1 for p in pages_lower
        if any(kw in p for kw in ["/features", "/product", "/solutions", "/platform"])
    )
    if product_pages >= 2:
        score += INTENT_WEIGHTS["multiple_product_pages"]
        reasons.append(f"Browsed {product_pages} product pages (+1.5)")

    if ctx.visits_this_week and ctx.visits_this_week >= 3:
        score += INTENT_WEIGHTS["multiple_visits_week"]
        reasons.append(f"{ctx.visits_this_week} visits this week (+2.0)")

    if ctx.time_on_site_seconds and ctx.time_on_site_seconds > 180:
        score += INTENT_WEIGHTS["long_session"]
        minutes = ctx.time_on_site_seconds // 60
        reasons.append(f"Session duration {minutes}+ minutes (+2.0)")

    if ctx.referral_source:
        source = ctx.referral_source.lower()
        if "linkedin" in source:
            score += INTENT_WEIGHTS["referral_linkedin"]
            reasons.append("LinkedIn referral (+0.5)")
        elif "google" in source:
            score += INTENT_WEIGHTS["referral_google"]
            reasons.append("Google search referral (+0.3)")

    blog_pages = sum(1 for p in pages_lower if "/blog" in p)
    if blog_pages > 0 and blog_pages == len(pages):
        score += INTENT_WEIGHTS["blog_only_penalty"]
        reasons.append("Blog-only session (-1.0)")

    score = max(0.0, min(10.0, score))

    stage = _map_score_to_stage(score)

    if not reasons:
        reasons.append("No high-intent signals detected")

    return IntentResult(
        score=round(score, 1),
        stage=stage,
        reasons=reasons,
    )


def _map_score_to_stage(score: float) -> IntentStage:
    """Map numeric intent score to funnel stage."""
    if score >= 8.0:
        return "Decision"
    elif score >= 5.0:
        return "Evaluation"
    elif score >= 3.0:
        return "Research"
    else:
        return "Awareness"


def get_default_intent_for_company_seed() -> IntentResult:
    """
    Return a default intent result for company-seed input path.
    
    When analyzing a company directly (not from visitor behavior),
    we have no behavioral signals to score intent.
    """
    return IntentResult(
        score=5.0,
        stage="Research",
        reasons=[
            "Company submitted directly (no visitor behavior data)",
            "Default score assumes moderate interest",
        ],
    )

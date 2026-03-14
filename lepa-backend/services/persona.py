from typing import Literal
from collections import Counter

from schemas.internal_models import NormalizedAccountInput
from schemas.output_models import PersonaResult


PageCategory = Literal["commercial", "proof", "technical", "educational", "product", "other"]


PAGE_CATEGORY_PATTERNS: dict[PageCategory, list[str]] = {
    "commercial": [
        "/pricing", "/plans", "/buy", "/purchase", "/checkout",
        "/quote", "/demo", "/trial", "/signup", "/contact-sales",
    ],
    "proof": [
        "/case-studies", "/case-study", "/customers", "/testimonials",
        "/success-stories", "/reviews", "/portfolio",
    ],
    "technical": [
        "/docs", "/documentation", "/api", "/developers", "/sdk",
        "/reference", "/guide", "/tutorial", "/integration",
    ],
    "educational": [
        "/blog", "/resources", "/learn", "/academy", "/webinar",
        "/ebook", "/whitepaper", "/newsletter",
    ],
    "product": [
        "/features", "/product", "/solutions", "/platform", "/tools",
        "/capabilities", "/use-cases", "/how-it-works",
    ],
}


PERSONA_RULES = {
    "Business Buyer": {
        "required": ["commercial"],
        "boost": ["proof", "product"],
        "description": "Likely decision-maker evaluating solutions for purchase",
    },
    "Technical Evaluator": {
        "required": ["technical"],
        "boost": ["product"],
        "description": "Technical stakeholder assessing implementation feasibility",
    },
    "Researcher": {
        "required": ["educational"],
        "boost": [],
        "description": "Early-stage prospect gathering information",
    },
}


def infer_persona(normalized_input: NormalizedAccountInput) -> PersonaResult:
    """
    Infer visitor persona from browsing behavior.
    
    Uses rule-based classification based on page categories visited.
    """
    pages = normalized_input.visitor_context.pages_visited

    if not pages:
        return PersonaResult(
            label="Unknown",
            confidence=0.0,
            reasons=["No pages visited - cannot infer persona"],
        )

    categories = [_categorize_page(page) for page in pages]
    category_counts = Counter(categories)
    
    total_pages = len(pages)
    reasons = []

    commercial_count = category_counts.get("commercial", 0)
    proof_count = category_counts.get("proof", 0)
    technical_count = category_counts.get("technical", 0)
    educational_count = category_counts.get("educational", 0)
    product_count = category_counts.get("product", 0)

    if commercial_count > 0:
        confidence = 0.6 + min(0.3, commercial_count * 0.1)
        reasons.append(f"Visited {commercial_count} commercial page(s) (pricing, demo, etc.)")

        if proof_count > 0:
            confidence += 0.1
            reasons.append(f"Also checked {proof_count} social proof page(s)")

        return PersonaResult(
            label="Business Buyer",
            confidence=min(1.0, confidence),
            reasons=reasons,
        )

    if technical_count > 0:
        confidence = 0.5 + min(0.3, technical_count * 0.1)
        reasons.append(f"Visited {technical_count} technical page(s) (docs, API, etc.)")

        if product_count > 0:
            confidence += 0.1
            reasons.append(f"Also explored {product_count} product page(s)")

        return PersonaResult(
            label="Technical Evaluator",
            confidence=min(1.0, confidence),
            reasons=reasons,
        )

    if educational_count > 0:
        confidence = 0.4 + min(0.2, educational_count * 0.05)
        reasons.append(f"Visited {educational_count} educational page(s) (blog, resources)")

        if educational_count == total_pages:
            reasons.append("Session focused entirely on educational content")
        else:
            confidence += 0.1
            reasons.append("Mixed with other content types")

        return PersonaResult(
            label="Researcher",
            confidence=min(1.0, confidence),
            reasons=reasons,
        )

    if product_count > 0:
        reasons.append(f"Browsed {product_count} product page(s)")
        return PersonaResult(
            label="Researcher",
            confidence=0.4,
            reasons=reasons + ["Product browsing without commercial signals suggests early research"],
        )

    reasons.append(f"Visited {total_pages} page(s) with no strong category signals")
    return PersonaResult(
        label="Unknown",
        confidence=0.2,
        reasons=reasons,
    )


def _categorize_page(page_path: str) -> PageCategory:
    """Categorize a page path into one of the defined categories."""
    path_lower = page_path.lower()

    for category, patterns in PAGE_CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in path_lower:
                return category

    return "other"


def extract_key_signals(normalized_input: NormalizedAccountInput) -> list[str]:
    """Extract notable behavioral signals for display."""
    signals = []
    ctx = normalized_input.visitor_context
    pages = ctx.pages_visited

    for page in pages:
        if "/pricing" in page.lower():
            signals.append("Viewed pricing page")
            break

    for page in pages:
        if any(p in page.lower() for p in ["/case-studies", "/customers"]):
            signals.append("Reviewed case studies")
            break

    for page in pages:
        if any(p in page.lower() for p in ["/docs", "/api"]):
            signals.append("Explored technical documentation")
            break

    if ctx.visits_this_week and ctx.visits_this_week >= 3:
        signals.append(f"Multiple visits this week ({ctx.visits_this_week})")

    if ctx.time_on_site_seconds and ctx.time_on_site_seconds > 300:
        minutes = ctx.time_on_site_seconds // 60
        signals.append(f"Extended session duration ({minutes} min)")

    if ctx.referral_source:
        source = ctx.referral_source.lower()
        if "linkedin" in source:
            signals.append("Came from LinkedIn")
        elif "google" in source:
            signals.append("Came from Google search")
        elif source == "direct":
            signals.append("Direct visit (possible brand awareness)")

    return signals

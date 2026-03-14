"""
Technology stack detection service.

Primary source: BuiltWith API (domain-level, comprehensive)
Fallback source: Page-scan from existing scraper (pattern matching on HTML)

Output is a deduplicated, categorized list of TechStackItem objects
with confidence and source attribution.
"""

from typing import Optional

from schemas.output_models import TechStackItem
from clients.builtwith_client import get_tech_stack, BuiltWithResponse
from clients.scraper import TECH_PATTERNS, _detect_technologies


SCRAPER_CATEGORY_MAP: dict[str, str] = {
    "react": "devtools",
    "vue": "devtools",
    "angular": "devtools",
    "next.js": "devtools",
    "wordpress": "cms",
    "shopify": "cms",
    "hubspot": "marketing_automation",
    "salesforce": "crm",
    "google_analytics": "analytics",
    "segment": "analytics",
    "intercom": "marketing_automation",
    "zendesk": "support",
    "stripe": "payments",
}


async def detect_tech_stack(
    domain: Optional[str],
    page_html: Optional[str] = None,
) -> list[TechStackItem]:
    """
    Detect technologies used by a company.

    Tries BuiltWith first. If unavailable or returns no results,
    falls back to pattern-matching the page HTML from the scraper.

    Args:
        domain: Company domain (e.g., 'stripe.com').
        page_html: Optional raw HTML from a prior page scrape.

    Returns:
        Deduplicated list of TechStackItem objects, most confident first.
    """
    if not domain:
        return []

    builtwith_result: BuiltWithResponse = await get_tech_stack(domain)

    if builtwith_result.success and builtwith_result.technologies:
        items = [
            TechStackItem(
                category=t.category,  # type: ignore[arg-type]
                name=t.name,
                confidence=t.confidence,
                source="builtwith",
            )
            for t in builtwith_result.technologies
        ]
        return _deduplicate(items)

    return _scan_from_html(page_html)


def _scan_from_html(html: Optional[str]) -> list[TechStackItem]:
    """
    Fallback: detect technologies from raw page HTML using scraper patterns.

    Assigns lower confidence (0.6) since this is pattern-matching only.
    """
    if not html:
        return []

    detected_names = _detect_technologies(html)
    items = []
    for name in detected_names:
        category = SCRAPER_CATEGORY_MAP.get(name, "other")
        items.append(
            TechStackItem(
                category=category,  # type: ignore[arg-type]
                name=name.replace("_", " ").title(),
                confidence=0.6,
                source="page_scan",
            )
        )

    return _deduplicate(items)


def _deduplicate(items: list[TechStackItem]) -> list[TechStackItem]:
    """Remove duplicate technology names, keeping the highest-confidence entry."""
    seen: dict[str, TechStackItem] = {}
    for item in items:
        key = item.name.lower()
        if key not in seen or item.confidence > seen[key].confidence:
            seen[key] = item
    return sorted(seen.values(), key=lambda x: x.confidence, reverse=True)

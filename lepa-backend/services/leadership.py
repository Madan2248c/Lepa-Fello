"""
Leadership discovery service.

Uses Exa neural search to find likely decision-makers for a company.
Targets CEO, Founder, VP Sales, Head of Marketing, RevOps, and similar
go-to-market relevant roles from public sources.

Falls back to LinkedIn employee data from the Apify scrape if available.
"""

import re
from typing import Optional

from schemas.output_models import LeadershipContact
from clients.exa_client import search_leadership


GTM_ROLE_PRIORITY: dict[str, int] = {
    "ceo": 10,
    "chief executive": 10,
    "founder": 9,
    "co-founder": 9,
    "president": 8,
    "cro": 8,
    "chief revenue": 8,
    "vp sales": 8,
    "vice president of sales": 8,
    "head of sales": 7,
    "vp marketing": 7,
    "vice president of marketing": 7,
    "head of marketing": 7,
    "cmo": 7,
    "chief marketing": 7,
    "revops": 6,
    "revenue operations": 6,
    "vp of revenue": 6,
    "coo": 6,
    "chief operating": 6,
    "cto": 5,
    "chief technology": 5,
    "vp product": 5,
    "head of product": 5,
    "director of sales": 5,
    "director of marketing": 5,
    "account executive": 3,
    "sales manager": 3,
    "marketing manager": 3,
}

NAME_PATTERN = re.compile(
    r"\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,25}(?:\s+[A-Z][a-z]{1,25})?)\b"
)

TITLE_PATTERNS = [
    re.compile(
        r"(CEO|CTO|CMO|COO|CRO|CFO|Founder|Co-Founder|President|"
        r"VP\s+(?:of\s+)?(?:Sales|Marketing|Product|Engineering|Revenue)|"
        r"Vice\s+President\s+of\s+(?:Sales|Marketing|Product)|"
        r"Head\s+of\s+(?:Sales|Marketing|Product|Revenue|Growth)|"
        r"Chief\s+(?:Executive|Revenue|Marketing|Operating|Technology|Financial)\s+Officer|"
        r"Director\s+of\s+(?:Sales|Marketing|Revenue)|"
        r"RevOps|Revenue\s+Operations)",
        re.I,
    )
]


async def discover_leadership(
    company_name: str,
    domain: Optional[str] = None,
    linkedin_employees: Optional[list[dict]] = None,
    max_contacts: int = 5,
) -> list[LeadershipContact]:
    """
    Discover likely decision-makers for a company.

    Strategy:
    1. Use Exa to search for leadership/team pages and executive profiles.
    2. Extract name/title pairs from result text.
    3. Supplement with LinkedIn employee data if available from Phase 1.
    4. Rank by GTM relevance and deduplicate.

    Args:
        company_name: Name of the company.
        domain: Optional domain to anchor Exa search.
        linkedin_employees: Optional employee list from Apify LinkedIn scrape.
        max_contacts: Maximum number of contacts to return.

    Returns:
        Ranked list of LeadershipContact objects.
    """
    contacts: list[LeadershipContact] = []

    exa_response = await search_leadership(
        company_name=company_name,
        domain=domain,
        num_results=5,
    )

    if exa_response.success and exa_response.results:
        for result in exa_response.results:
            extracted = _extract_contacts_from_text(
                text=result.text or "",
                source_url=result.url,
                base_confidence=0.7,
            )
            contacts.extend(extracted)

    if linkedin_employees:
        for employee in linkedin_employees[:10]:
            name = employee.get("name") or ""
            title = employee.get("title") or employee.get("position") or ""
            if name and title and _is_gtm_relevant(title):
                contacts.append(
                    LeadershipContact(
                        name=name.strip(),
                        title=title.strip(),
                        source_url=None,
                        confidence=0.8,
                    )
                )

    contacts = _deduplicate_contacts(contacts)
    contacts = _rank_by_gtm_relevance(contacts)
    return contacts[:max_contacts]


def _extract_contacts_from_text(
    text: str,
    source_url: Optional[str],
    base_confidence: float,
) -> list[LeadershipContact]:
    """
    Extract name/title pairs from free text using regex heuristics.

    Looks for patterns like "Jane Smith, CEO" or "John Doe - VP Sales".
    Only returns contacts where the title matches a GTM-relevant role.
    """
    if not text:
        return []

    contacts: list[LeadershipContact] = []
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if len(line) < 5 or len(line) > 200:
            continue

        title_match = None
        for pattern in TITLE_PATTERNS:
            m = pattern.search(line)
            if m:
                title_match = m
                break

        if not title_match:
            continue

        name_match = NAME_PATTERN.search(line)
        if not name_match:
            continue

        name = name_match.group(0).strip()
        title = title_match.group(0).strip()

        if name.lower() in title.lower() or title.lower() in name.lower():
            continue

        if len(name.split()) < 2:
            continue

        contacts.append(
            LeadershipContact(
                name=name,
                title=title,
                source_url=source_url,
                confidence=base_confidence,
            )
        )

    return contacts


def _is_gtm_relevant(title: str) -> bool:
    """Return True if a title is relevant to go-to-market outreach."""
    title_lower = title.lower()
    return any(role in title_lower for role in GTM_ROLE_PRIORITY)


def _rank_by_gtm_relevance(contacts: list[LeadershipContact]) -> list[LeadershipContact]:
    """Sort contacts by GTM role priority (highest first)."""

    def priority(contact: LeadershipContact) -> int:
        title_lower = contact.title.lower()
        for role, score in GTM_ROLE_PRIORITY.items():
            if role in title_lower:
                return score
        return 0

    return sorted(contacts, key=priority, reverse=True)


def _deduplicate_contacts(contacts: list[LeadershipContact]) -> list[LeadershipContact]:
    """Remove duplicate contacts by normalized name."""
    seen: dict[str, LeadershipContact] = {}
    for contact in contacts:
        key = re.sub(r"\s+", " ", contact.name.lower().strip())
        if key not in seen or contact.confidence > seen[key].confidence:
            seen[key] = contact
    return list(seen.values())

"""
Leadership discovery: Exa people search → Apify batch scrape → Haiku verification.
"""

import re
import json
import logging
from typing import Optional

from schemas.output_models import LeadershipContact

logger = logging.getLogger(__name__)

GTM_ROLE_PRIORITY: dict[str, int] = {
    "ceo": 10, "chief executive": 10,
    "founder": 9, "co-founder": 9,
    "president": 8, "cro": 8, "chief revenue": 8,
    "vp sales": 8, "vice president of sales": 8, "head of sales": 7,
    "vp marketing": 7, "vice president of marketing": 7, "head of marketing": 7,
    "cmo": 7, "chief marketing": 7,
    "revops": 6, "revenue operations": 6, "vp of revenue": 6,
    "coo": 6, "chief operating": 6,
    "cto": 5, "chief technology": 5,
    "vp product": 5, "head of product": 5,
    "director of sales": 5, "director of marketing": 5,
}

GTM_TITLES = [
    "CEO", "Founder", "Co-Founder", "President",
    "CRO", "Chief Revenue Officer",
    "VP Sales", "VP of Sales", "Head of Sales", "Director of Sales",
    "CMO", "VP Marketing", "VP of Marketing", "Head of Marketing", "Chief Marketing Officer",
    "COO", "Chief Operating Officer",
    "CTO", "VP Product", "Head of Product",
]


async def discover_leadership(
    company_name: str,
    domain: Optional[str] = None,
    linkedin_employees: Optional[list[dict]] = None,
    max_contacts: int = 5,
) -> tuple[list[LeadershipContact], dict]:

    # Step 1: Exa people search → collect candidate LinkedIn URLs
    candidate_urls: list[dict] = []
    seen_urls: set = set()
    try:
        from clients.exa_client import search_people
        for role in GTM_TITLES[:10]:
            response = await search_people(f"{role} at {company_name}", num_results=3)
            if not response.success:
                continue
            for result in response.results:
                url = result.url
                if url in seen_urls or "linkedin.com/in/" not in url:
                    continue
                seen_urls.add(url)
                candidate_urls.append({
                    "url": url,
                    "name": result.person_name or "",
                    "title": result.person_title or result.title or "",
                })
    except Exception as e:
        logger.warning(f"Exa search failed: {e}")

    if not candidate_urls:
        return [], {}

    # Cap at 10 before Apify
    candidate_urls = candidate_urls[:10]

    # Step 2: Apify batch scrape all candidates
    scraped_profiles: dict = {}
    try:
        from clients.apify_linkedin_person_client import scrape_linkedin_persons
        urls = [c["url"] for c in candidate_urls]
        profiles = await scrape_linkedin_persons(urls)
        scraped_profiles = {p.linkedin_url.rstrip("/"): p for p in profiles if p.success}
        logger.info(f"Apify scraped {len(scraped_profiles)}/{len(urls)} profiles successfully")
    except Exception as e:
        logger.warning(f"Apify scrape failed: {e}")

    # Step 3: Haiku verification — batch verify current company in one LLM call
    verified: list[LeadershipContact] = []
    if scraped_profiles:
        verified = await _verify_with_haiku(candidate_urls, scraped_profiles, company_name)

    # If Haiku verified nobody (all spam / all 403), fall back to Haiku knowledge-based generation
    if not verified:
        logger.info(f"No verified contacts from Exa+Apify, using Haiku knowledge for {company_name}")
        verified = await _generate_from_knowledge(company_name, max_contacts)

    verified = _deduplicate(verified)
    verified = _rank(verified)
    return verified[:max_contacts], scraped_profiles


async def _generate_from_knowledge(company_name: str, max_contacts: int) -> list[LeadershipContact]:
    """Use Haiku's training knowledge to name likely current executives at well-known companies."""
    from clients.bedrock_client import invoke_claude
    prompt = f"""List the current GTM-relevant executives at "{company_name}" (CEO, President, CRO, CMO, VP Sales, COO, etc.).
Use only well-known, publicly confirmed current leaders. If unsure, omit.
Return ONLY a JSON array: [{{"name":"Full Name","title":"Exact Title"}}]
Max {max_contacts} people."""
    try:
        raw = await invoke_claude(prompt, model="haiku", max_tokens=400, temperature=0)
        if not raw:
            return []
        items = json.loads(raw[raw.find("["):raw.rfind("]") + 1])
        return [
            LeadershipContact(name=i["name"], title=i["title"], source_url=None, confidence=0.75)
            for i in items if i.get("name") and i.get("title") and _is_gtm_relevant(i["title"])
        ]
    except Exception as e:
        logger.warning(f"Knowledge-based generation failed: {e}")
        return []


async def _verify_with_haiku(
    candidates: list[dict],
    scraped_profiles: dict,
    company_name: str,
) -> list[LeadershipContact]:
    """Single Haiku call to verify all scraped profiles at once."""
    from clients.bedrock_client import invoke_claude

    profiles_text = []
    for c in candidates:
        url_key = c["url"].rstrip("/")
        profile = scraped_profiles.get(url_key)
        if not profile:
            continue
        exp_summary = "; ".join(
            f"{e.get('position','?')} at {e.get('companyName','?')} (end: {(e.get('endDate') or {}).get('text','present')})"
            for e in (profile.experience or [])[:4]
        )
        profiles_text.append(
            f"ID:{url_key}\nName:{profile.full_name}\nHeadline:{profile.headline}\nExperience:{exp_summary}"
        )

    if not profiles_text:
        return []

    prompt = f"""For each profile below, determine if the person CURRENTLY works at "{company_name}".
Return ONLY a JSON array: [{{"id":"linkedin_url","works_here":true/false,"current_title":"their title at {company_name} or null"}}]

Profiles:
{chr(10).join(profiles_text)}"""

    try:
        raw = await invoke_claude(prompt, model="haiku", max_tokens=800, temperature=0)
        if not raw:
            raise ValueError("Empty response from Haiku")
        results = json.loads(raw[raw.find("["):raw.rfind("]") + 1])
    except Exception as e:
        logger.warning(f"Haiku verification failed: {e}")
        # Fallback: include all scraped profiles without verification
        contacts = []
        for c in candidates:
            url_key = c["url"].rstrip("/")
            p = scraped_profiles.get(url_key)
            if p and _is_gtm_relevant(p.current_title or c["title"]):
                contacts.append(LeadershipContact(
                    name=p.full_name, title=p.current_title or c["title"],
                    source_url=c["url"], confidence=0.7,
                ))
        return contacts

    contacts = []
    for item in results:
        if not item.get("works_here"):
            continue
        url_key = (item.get("id") or "").rstrip("/")
        profile = scraped_profiles.get(url_key)
        if not profile:
            continue
        title = item.get("current_title") or profile.current_title or ""
        if title and _is_gtm_relevant(title):
            contacts.append(LeadershipContact(
                name=profile.full_name,
                title=title,
                source_url=profile.linkedin_url,
                confidence=0.9,
            ))
    return contacts


def _is_gtm_relevant(title: str) -> bool:
    t = title.lower()
    return any(role in t for role in GTM_ROLE_PRIORITY)


def _rank(contacts: list[LeadershipContact]) -> list[LeadershipContact]:
    def priority(c: LeadershipContact) -> int:
        t = c.title.lower()
        return max((s for r, s in GTM_ROLE_PRIORITY.items() if r in t), default=0)
    return sorted(contacts, key=priority, reverse=True)


def _deduplicate(contacts: list[LeadershipContact]) -> list[LeadershipContact]:
    seen: dict[str, LeadershipContact] = {}
    for c in contacts:
        key = re.sub(r"\s+", " ", c.name.lower().strip())
        if key not in seen or c.confidence > seen[key].confidence:
            seen[key] = c
    return list(seen.values())

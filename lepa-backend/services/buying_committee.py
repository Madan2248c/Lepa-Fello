"""
Buying committee mapping service.

Classifies discovered leadership contacts into buying committee roles using LLM reasoning:
- Economic Buyer (controls budget)
- Champion (internal advocate)
- Technical Evaluator (validates fit)
- End User (daily operator)
- Blocker (legal/security/procurement)

Then optionally enriches each member with LinkedIn person profile data.
"""

import asyncio
import logging
from typing import Optional

from clients.bedrock_client import invoke_claude
from schemas.output_models import LeadershipContact
from clients.apify_linkedin_person_client import scrape_linkedin_persons, LinkedInPersonProfile

logger = logging.getLogger("lepa.buying_committee")

COMMITTEE_PROMPT = """You are a B2B sales expert. Classify each person into a buying committee role based on their title, company context, and industry.

BUYING COMMITTEE ROLES:
- Economic Buyer: Controls final budget and strategic decisions (CEO, President, Owner, Founder, CFO for budget approval)
- Champion: Drives internal adoption and champions the deal (VP Sales, CRO, Head of Sales, Sales Director, Product VP)
- Technical Evaluator: Validates technical fit and integration requirements (CTO, VP Engineering, Head of Engineering, Architect, DevOps Lead)
- End User: Day-to-day operator of the solution (Account Executive, SDR, BDR, Sales Rep, Customer Success)
- Blocker: Controls contracts, legal review, and budget approval (CFO, Legal Counsel, Compliance Officer, Procurement)

INPUT:
Name: {name}
Title: {title}
Company: {company}
Industry: {industry}

OUTPUT FORMAT (JSON only):
{{
  "role": "Economic Buyer" | "Champion" | "Technical Evaluator" | "End User" | "Blocker",
  "rationale": "1-2 sentence explanation based on title and company context"
}}"""


def _extract_linkedin_url(contact: LeadershipContact, company_name: str = "") -> Optional[str]:
    """Extract LinkedIn URL from source_url if it's already a LinkedIn link."""
    if contact.source_url and "linkedin.com/in/" in contact.source_url:
        return contact.source_url
    return None


async def _find_linkedin_url(name: str, title: str, company_name: str) -> Optional[str]:
    """
    Use Exa People Search to find LinkedIn profile URL.
    Uses individual lookup pattern: "Name at Company"
    """
    from clients.exa_client import search_people
    
    # Individual lookup: "Name at Company"
    query = f"{name} at {company_name}"
    response = await search_people(query, num_results=3)
    
    if response.success and response.results:
        company_lower = company_name.lower()
        
        for result in response.results:
            url = result.url
            title_text = result.title.lower()
            
            # Validate: LinkedIn URL + company name in title
            if "linkedin.com/in/" in url and company_lower in title_text:
                return url
    
    return None


async def build_buying_committee(
    leadership: list[LeadershipContact],
    enrich_with_linkedin: bool = True,
    company_name: str = "",
    industry: str = "",
    tenant_id: str = "default",
    prefetched_profiles: dict = None,  # url -> LinkedInPersonProfile, already scraped in leadership
) -> list[dict]:
    """
    Build a buying committee from leadership contacts using LLM classification.
    Prioritizes roles that match ICP target roles.

    Each member gets:
    - name, title, role, rationale, confidence
    - linkedin_profile (if enriched): headline, about, top_skills, experience summary

    Args:
        leadership: Discovered leadership contacts from Phase 2.
        enrich_with_linkedin: Whether to scrape LinkedIn person profiles.
        company_name: Company name for context.
        industry: Industry for context.
        tenant_id: Tenant ID to get ICP target roles.

    Returns:
        List of buying committee member dicts.
    """
    if not leadership:
        return []

    # Get ICP target roles for prioritization
    from services.icp_profile import get_icp_profile
    icp_profile = get_icp_profile(tenant_id)
    target_roles = icp_profile.get("target_roles", [])
    
    # Filter and prioritize leadership based on ICP target roles
    prioritized_leadership = []
    other_leadership = []
    
    for contact in leadership:
        contact_title_lower = contact.title.lower()
        matches_icp = any(
            target_role.lower() in contact_title_lower or contact_title_lower in target_role.lower()
            for target_role in target_roles
        )
        
        if matches_icp:
            prioritized_leadership.append(contact)
        else:
            other_leadership.append(contact)
    
    # Use prioritized contacts first, then others (limit total to avoid too many API calls)
    contacts_to_process = prioritized_leadership + other_leadership[:max(0, 8 - len(prioritized_leadership))]
    
    if not contacts_to_process:
        contacts_to_process = leadership[:8]  # Fallback if no ICP matches

    # Classify all roles in parallel using Haiku
    tasks = []
    for contact in contacts_to_process:
        # Enhanced prompt that includes ICP target roles
        enhanced_prompt = COMMITTEE_PROMPT + f"""

PRIORITY ROLES (from ICP): {', '.join(target_roles) if target_roles else 'None specified'}

When classifying, give higher confidence to roles that match the ICP target roles above.

Person to classify:
Name: {contact.name}
Title: {contact.title}
Company: {company_name or "Unknown"}
Industry: {industry or "Unknown"}

Classify this person into one of the buying committee roles."""
        
        tasks.append(_classify_role_llm(enhanced_prompt, contact))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    committee = []
    linkedin_urls_to_scrape = []
    url_to_index = {}

    for i, result in enumerate(results):
        contact = contacts_to_process[i]
        if isinstance(result, Exception) or not result:
            # Fallback to simple rule-based if LLM fails
            role, rationale = _fallback_classify(contact.title)
        else:
            role, rationale = result

        member = {
            "name": contact.name,
            "title": contact.title,
            "role": role,
            "rationale": rationale,
            "confidence": contact.confidence * 0.9,  # Slightly lower confidence for LLM classification
            "source_url": contact.source_url,  # Will be updated to LinkedIn URL if found
            "linkedin_profile": None,
        }
        committee.append(member)

        if enrich_with_linkedin:
            # First check if source_url is already a LinkedIn URL
            li_url = _extract_linkedin_url(contact, company_name)
            
            # If not, use Exa People Search to find it
            if not li_url:
                li_url = await _find_linkedin_url(contact.name, contact.title, company_name)
            
            if li_url:
                url_to_index[li_url] = i
                linkedin_urls_to_scrape.append(li_url)
                # Update source_url to LinkedIn URL
                member["source_url"] = li_url

    if linkedin_urls_to_scrape:
        try:
            prefetched = {k.rstrip("/"): v for k, v in (prefetched_profiles or {}).items()}
            missing_urls = [u for u in linkedin_urls_to_scrape if u.rstrip("/") not in prefetched]

            scraped = {}
            if missing_urls:
                fresh = await scrape_linkedin_persons(missing_urls, target_company=company_name)
                scraped = {p.linkedin_url.rstrip("/"): p for p in fresh if p.success}

            all_profiles = {**prefetched, **scraped}

            for url, idx in url_to_index.items():
                profile = all_profiles.get(url.rstrip("/"))
                if profile and profile.success:
                    committee[idx]["linkedin_profile"] = _summarize_person_profile(profile)
        except Exception as e:
            logger.warning(f"LinkedIn person enrichment failed: {e}")

    return committee


async def _classify_role_llm(prompt: str, contact: LeadershipContact) -> Optional[tuple[str, str]]:
    """Classify a role using Haiku LLM."""
    try:
        response = await invoke_claude(
            prompt=prompt,
            model="haiku",
            max_tokens=500,
        )
        # Try to parse JSON from response
        import json
        import re
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            role = data.get("role", "Influencer")
            rationale = data.get("rationale", "LLM classification")
            # Validate role
            valid_roles = ["Economic Buyer", "Champion", "Technical Evaluator", "End User", "Blocker"]
            if role not in valid_roles:
                role = "Influencer"
                rationale = f"LLM classified as '{role}' — fallback to Influencer"
            return role, rationale
        return None
    except Exception as e:
        logger.warning(f"LLM role classification failed for {contact.name}: {e}")
        return None


def _fallback_classify(title: str) -> tuple[str, str]:
    """Fallback rule-based classification if LLM fails."""
    title_lower = title.lower()
    rules = [
        (["ceo", "chief executive", "president", "founder", "co-founder", "owner"], "Economic Buyer", "Controls final budget and strategic decisions"),
        (["cro", "chief revenue", "vp sales", "vice president of sales", "head of sales", "director of sales", "sales manager"], "Champion", "Drives internal adoption and champions the deal"),
        (["cto", "chief technology", "vp engineering", "head of engineering", "architect", "devops", "security", "it director"], "Technical Evaluator", "Validates technical fit and integration requirements"),
        (["cmo", "chief marketing", "vp marketing", "head of marketing"], "Champion", "Marketing champion for revenue tools"),
        (["cfo", "chief financial", "finance", "procurement", "legal", "compliance", "counsel"], "Blocker", "Controls contracts, legal review, and budget approval"),
        (["account executive", "sales rep", "sdr", "bdr", "account manager"], "End User", "Day-to-day operator of the solution"),
    ]
    for keywords, role, rationale in rules:
        if any(kw in title_lower for kw in keywords):
            return role, rationale
    return "Influencer", "Likely involved in evaluation or rollout"


def _summarize_person_profile(profile: LinkedInPersonProfile) -> dict:
    """Extract the most sales-relevant fields from a LinkedIn person profile."""
    recent_exp = []
    for exp in profile.experience[:3]:
        recent_exp.append({
            "company": exp.get("companyName"),
            "title": exp.get("position"),
            "duration": exp.get("duration"),
        })

    return {
        "headline": profile.headline,
        "about_snippet": (profile.about or "")[:300] or None,
        "location": profile.location,
        "top_skills": profile.top_skills,
        "connections": profile.connections_count,
        "recent_experience": recent_exp,
        "skills_sample": profile.skills[:10],
    }

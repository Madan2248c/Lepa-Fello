"""
Apify LinkedIn Person Profile Scraper client.

Uses `harvestapi/linkedin-profile-scraper` Actor to extract detailed
individual profile data: experience, education, skills, headline.
"""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from apify_client import ApifyClient

logger = logging.getLogger("lepa.apify_person")

ACTOR_ID = "harvestapi/linkedin-profile-scraper"


@dataclass
class LinkedInPersonProfile:
    linkedin_url: str
    public_identifier: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    headline: Optional[str] = None
    about: Optional[str] = None
    location: Optional[str] = None
    current_company: Optional[str] = None
    current_title: Optional[str] = None
    top_skills: Optional[str] = None
    connections_count: Optional[int] = None
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown"


def _scrape_person_sync(linkedin_urls: list[str], target_company: str = "") -> list[LinkedInPersonProfile]:
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        return [LinkedInPersonProfile(linkedin_url=u, error="APIFY_API_TOKEN not configured") for u in linkedin_urls]

    client = ApifyClient(api_token)
    run_input = {
        "profileScraperMode": "Profile details no email ($4 per 1k)",
        "queries": linkedin_urls,
    }

    try:
        logger.info(f"Starting LinkedIn person scrape for {len(linkedin_urls)} profiles")
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        results = []
        for item in items:
            exp = item.get("experience") or []
            active = [e for e in exp if (e.get("endDate") or {}).get("text") == "Present"]

            # Try to find the role at the target company first
            target_role = None
            if target_company:
                tc_lower = target_company.lower()
                target_role = next(
                    (e for e in active if tc_lower in (e.get("companyName") or "").lower()),
                    None
                )

            if target_role:
                current = target_role
            elif active:
                # Among active roles, pick the one with the most tenure (earliest start year)
                def start_year(e):
                    return (e.get("startDate") or {}).get("year") or 9999
                current = min(active, key=start_year)
            else:
                current = exp[0] if exp else {}

            results.append(LinkedInPersonProfile(
                linkedin_url=item.get("linkedinUrl", ""),
                public_identifier=item.get("publicIdentifier"),
                first_name=item.get("firstName"),
                last_name=item.get("lastName"),
                headline=item.get("headline"),
                about=item.get("about"),
                location=(item.get("location") or {}).get("linkedinText"),
                current_company=current.get("companyName"),
                current_title=current.get("position"),
                top_skills=item.get("topSkills"),
                connections_count=item.get("connectionsCount"),
                experience=exp[:5],
                education=item.get("education") or [],
                skills=[s.get("name", "") for s in (item.get("skills") or [])[:20]],
                success=True,
            ))
        return results
    except Exception as e:
        logger.error(f"LinkedIn person scrape failed: {e}")
        return [LinkedInPersonProfile(linkedin_url=u, error=str(e)[:200]) for u in linkedin_urls]


async def scrape_linkedin_persons(linkedin_urls: list[str], target_company: str = "") -> list[LinkedInPersonProfile]:
    """Scrape multiple LinkedIn person profiles in one Apify run."""
    if not linkedin_urls:
        return []
    return await asyncio.to_thread(_scrape_person_sync, linkedin_urls, target_company)

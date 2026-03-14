"""
Apify LinkedIn Company Profile Scraper client.

Uses the `scrapeverse/linkedin-company-profile-scraper-pay-per-event` Actor
to extract structured data from LinkedIn company pages.

The Apify client is synchronous so we run it in a thread pool to avoid
blocking FastAPI's async event loop.
"""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from apify_client import ApifyClient

logger = logging.getLogger("lepa.apify")

ACTOR_ID = "scrapeverse/linkedin-company-profile-scraper-pay-per-event"


@dataclass
class LinkedInCompanyProfile:
    """Structured data extracted from a LinkedIn company page."""

    company_name: Optional[str] = None
    tagline: Optional[str] = None
    about: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    company_size_on_linkedin: Optional[int] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    founded: Optional[str] = None
    company_type: Optional[str] = None
    specialties: Optional[str] = None
    follower_count: Optional[str] = None
    linkedin_url: Optional[str] = None
    employees: list[dict] = field(default_factory=list)
    locations: list[dict] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


def _clean_website_url(raw: Optional[str]) -> Optional[str]:
    """LinkedIn wraps external URLs in a redirect. Extract the real URL."""
    if not raw:
        return None
    if "linkedin.com/redir/redirect" in raw:
        try:
            from urllib.parse import urlparse, parse_qs, unquote
            parsed = urlparse(raw)
            qs = parse_qs(parsed.query)
            if "url" in qs:
                return unquote(qs["url"][0])
        except Exception:
            pass
    return raw


def _scrape_sync(linkedin_url: str) -> LinkedInCompanyProfile:
    """
    Synchronous Apify call — runs in a thread pool via asyncio.to_thread.
    """
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        return LinkedInCompanyProfile(error="APIFY_API_TOKEN not configured")

    client = ApifyClient(api_token)

    run_input = {
        "urls": [linkedin_url],
        "proxy": {"useApifyProxy": True},
    }

    try:
        logger.info(f"Starting Apify LinkedIn scrape for: {linkedin_url}")
        run = client.actor(ACTOR_ID).call(run_input=run_input)

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return LinkedInCompanyProfile(
                linkedin_url=linkedin_url,
                error="No data returned from LinkedIn scraper",
            )

        data = items[0]
        logger.info(f"LinkedIn scrape complete for: {data.get('company_name', 'unknown')}")

        employees = [
            {
                "name": e.get("employee_name"),
                "position": e.get("employee_position"),
                "profile_url": e.get("employee_profile_url"),
                "photo": e.get("employee_photo"),
            }
            for e in (data.get("employees") or [])
        ]

        locations = data.get("locations") or []

        return LinkedInCompanyProfile(
            company_name=data.get("company_name"),
            tagline=data.get("tagline"),
            about=data.get("about"),
            industry=data.get("industry") or data.get("industries"),
            company_size=data.get("company_size"),
            company_size_on_linkedin=data.get("company_size_on_linkedin"),
            headquarters=data.get("headquarters") or data.get("location"),
            website=_clean_website_url(data.get("website")),
            founded=str(data.get("founded")) if data.get("founded") else None,
            company_type=data.get("type"),
            specialties=data.get("specialties"),
            follower_count=data.get("follower_count"),
            linkedin_url=linkedin_url,
            employees=employees,
            locations=locations,
            success=True,
        )

    except Exception as e:
        logger.error(f"Apify LinkedIn scrape failed: {e}")
        return LinkedInCompanyProfile(
            linkedin_url=linkedin_url,
            error=f"Apify scrape failed: {str(e)[:200]}",
        )


async def scrape_linkedin_company(linkedin_url: str) -> LinkedInCompanyProfile:
    """
    Scrape a LinkedIn company page using the Apify Actor.

    Args:
        linkedin_url: Slug-based LinkedIn URL, e.g.
                      'https://www.linkedin.com/company/stripe'

    Returns:
        LinkedInCompanyProfile with extracted data.
    """
    if not linkedin_url:
        return LinkedInCompanyProfile(error="No LinkedIn URL provided")

    if not linkedin_url.startswith("http"):
        linkedin_url = f"https://www.linkedin.com/company/{linkedin_url}"

    return await asyncio.to_thread(_scrape_sync, linkedin_url)

"""
BuiltWith API client for technology stack detection.

BuiltWith's Domain API returns current and historical technology information
for any website — CRM, marketing automation, analytics, CMS, and more.

Docs: https://api.builtwith.com/domain-api
"""

import os
from typing import Optional
from dataclasses import dataclass, field

import httpx


BUILTWITH_API_BASE = "https://api.builtwith.com/v21/api.json"

CATEGORY_MAP: dict[str, str] = {
    # CRM
    "salesforce": "crm",
    "hubspot crm": "crm",
    "zoho crm": "crm",
    "pipedrive": "crm",
    "dynamics 365": "crm",
    "freshsales": "crm",
    # Marketing automation
    "hubspot": "marketing_automation",
    "marketo": "marketing_automation",
    "pardot": "marketing_automation",
    "mailchimp": "marketing_automation",
    "klaviyo": "marketing_automation",
    "activecampaign": "marketing_automation",
    "intercom": "marketing_automation",
    "drift": "marketing_automation",
    # CMS / website platform
    "wordpress": "cms",
    "drupal": "cms",
    "joomla": "cms",
    "webflow": "cms",
    "squarespace": "cms",
    "wix": "cms",
    "shopify": "cms",
    "contentful": "cms",
    # Analytics
    "google analytics": "analytics",
    "segment": "analytics",
    "mixpanel": "analytics",
    "amplitude": "analytics",
    "heap": "analytics",
    "fullstory": "analytics",
    "hotjar": "analytics",
    "pendo": "analytics",
    # Payments
    "stripe": "payments",
    "braintree": "payments",
    "paypal": "payments",
    "recurly": "payments",
    "chargebee": "payments",
    # Support
    "zendesk": "support",
    "freshdesk": "support",
    "intercom": "support",
    "helpscout": "support",
    # Dev tools / infra
    "cloudflare": "hosting",
    "aws": "hosting",
    "google cloud": "hosting",
    "azure": "hosting",
    "fastly": "hosting",
    "vercel": "hosting",
    "netlify": "hosting",
}


@dataclass
class BuiltWithTech:
    """A single technology detected by BuiltWith."""

    name: str
    category: str
    confidence: float = 0.8
    source: str = "builtwith"


@dataclass
class BuiltWithResponse:
    """Response from BuiltWith domain lookup."""

    technologies: list[BuiltWithTech] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


async def get_tech_stack(domain: str) -> BuiltWithResponse:
    """
    Look up the technology stack for a domain using BuiltWith.

    Args:
        domain: Company domain (e.g., 'stripe.com').

    Returns:
        BuiltWithResponse with detected technologies and categories.
    """
    api_key = os.getenv("BUILTWITH_API_KEY")
    if not api_key:
        return BuiltWithResponse(success=False, error="BUILTWITH_API_KEY not configured")

    if not domain:
        return BuiltWithResponse(success=False, error="No domain provided")

    clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    params = {
        "KEY": api_key,
        "LOOKUP": clean_domain,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(BUILTWITH_API_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        technologies = _parse_builtwith_response(data)
        return BuiltWithResponse(technologies=technologies, success=True)

    except httpx.HTTPStatusError as e:
        return BuiltWithResponse(
            success=False,
            error=f"BuiltWith API error {e.response.status_code}",
        )
    except Exception as e:
        return BuiltWithResponse(success=False, error=f"BuiltWith lookup failed: {str(e)[:150]}")


def _parse_builtwith_response(data: dict) -> list[BuiltWithTech]:
    """
    Parse BuiltWith v21 API response into a flat list of technologies.

    The v21 response nests technologies under Results -> Result -> Paths -> Technologies.
    We flatten this and map each technology name to a category.
    """
    techs: list[BuiltWithTech] = []
    seen: set[str] = set()

    results = data.get("Results", [])
    for result in results:
        paths = result.get("Result", {}).get("Paths", [])
        for path in paths:
            for tech in path.get("Technologies", []):
                name = tech.get("Name") or ""
                if not name or name.lower() in seen:
                    continue
                seen.add(name.lower())

                category = _map_category(name)
                techs.append(
                    BuiltWithTech(
                        name=name,
                        category=category,
                        confidence=0.9,
                        source="builtwith",
                    )
                )

    return techs[:30]


def _map_category(tech_name: str) -> str:
    """Map a technology name to a category using the CATEGORY_MAP."""
    name_lower = tech_name.lower()
    for key, category in CATEGORY_MAP.items():
        if key in name_lower:
            return category
    return "other"

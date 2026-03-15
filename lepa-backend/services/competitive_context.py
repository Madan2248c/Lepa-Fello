"""
Competitive context discovery service.

Uses Exa to find what competitors a company mentions, uses, or competes with.
Surfaces competitive intelligence useful for sales positioning.
"""

import re
import logging
from typing import Optional

from clients.exa_client import _exa_search
import os

logger = logging.getLogger("lepa.competitive_context")

# Common B2B software categories and their known competitors
COMPETITOR_SIGNALS: dict[str, list[str]] = {
    "crm": ["salesforce", "hubspot", "pipedrive", "zoho", "dynamics", "sugar crm"],
    "marketing_automation": ["marketo", "pardot", "eloqua", "mailchimp", "klaviyo", "activecampaign"],
    "analytics": ["google analytics", "mixpanel", "amplitude", "heap", "segment", "looker", "tableau"],
    "data_enrichment": ["zoominfo", "apollo", "clearbit", "lusha", "cognism", "6sense", "demandbase"],
    "support": ["zendesk", "intercom", "freshdesk", "servicenow", "drift"],
    "payments": ["stripe", "braintree", "adyen", "square", "paypal"],
    "devtools": ["github", "gitlab", "jira", "confluence", "linear", "notion"],
    "cloud": ["aws", "azure", "gcp", "google cloud"],
}


async def discover_competitive_context(
    company_name: str,
    domain: Optional[str] = None,
    tech_stack_names: Optional[list[str]] = None,
) -> dict:
    """
    Discover competitive context for a company.

    Returns:
        Dict with:
        - current_vendors: list of detected vendor/tool names
        - competitor_categories: which categories they're invested in
        - displacement_opportunities: tools they use that we might replace
        - competitive_mentions: any competitor names found in public content
        - positioning_notes: list of sales positioning suggestions
    """
    api_key = os.getenv("EXA_API_KEY")
    current_vendors = list(tech_stack_names or [])
    competitor_categories: dict[str, list[str]] = {}
    competitive_mentions: list[str] = []

    # Map known tech stack to categories
    for category, vendors in COMPETITOR_SIGNALS.items():
        matched = [v for v in vendors if any(v in name.lower() for name in current_vendors)]
        if matched:
            competitor_categories[category] = matched

    # Search for competitive mentions in public content
    if api_key and company_name:
        try:
            query = f"{company_name} uses software tools technology stack competitors alternatives"
            response = await _exa_search(
                api_key=api_key,
                query=query,
                num_results=5,
                include_text=True,
                use_autoprompt=False,
                exclude_domains=["linkedin.com"],
            )
            if response.success:
                for result in response.results:
                    text = (result.text or "").lower()
                    for category, vendors in COMPETITOR_SIGNALS.items():
                        for vendor in vendors:
                            if vendor in text and vendor not in competitive_mentions:
                                competitive_mentions.append(vendor)
                                if category not in competitor_categories:
                                    competitor_categories[category] = []
                                if vendor not in competitor_categories[category]:
                                    competitor_categories[category].append(vendor)
        except Exception as e:
            logger.warning(f"Competitive context search failed: {e}")

    displacement_opportunities = _identify_displacement_opportunities(competitor_categories)
    positioning_notes = _generate_positioning_notes(competitor_categories, company_name)

    return {
        "current_vendors": current_vendors[:10],
        "competitor_categories": competitor_categories,
        "competitive_mentions": competitive_mentions[:10],
        "displacement_opportunities": displacement_opportunities,
        "positioning_notes": positioning_notes,
    }


def _identify_displacement_opportunities(categories: dict[str, list[str]]) -> list[dict]:
    """Identify tools that could be displaced or complemented."""
    opportunities = []

    displacement_map = {
        "crm": "If they use Salesforce/HubSpot, position as a native integration or enrichment layer",
        "data_enrichment": "They already invest in data enrichment — position as a superior/complementary source",
        "marketing_automation": "Active marketing stack — likely receptive to intent data and account intelligence",
        "analytics": "Analytics-mature team — will appreciate data quality and confidence scoring",
    }

    for category, vendors in categories.items():
        if category in displacement_map:
            opportunities.append({
                "category": category,
                "detected_vendors": vendors,
                "opportunity": displacement_map[category],
            })

    return opportunities


def _generate_positioning_notes(categories: dict[str, list[str]], company_name: str) -> list[str]:
    notes = []

    if "crm" in categories:
        crm_vendors = categories["crm"]
        notes.append(f"CRM-integrated: {company_name} uses {', '.join(crm_vendors)} — lead with native CRM sync")

    if "data_enrichment" in categories:
        notes.append("Already buys data enrichment — focus on accuracy, freshness, and AI differentiation vs incumbents")

    if "marketing_automation" in categories:
        notes.append("Marketing automation in place — position around sales-marketing alignment and intent signals")

    if "analytics" in categories:
        notes.append("Analytics-savvy team — lead with data quality, confidence scores, and measurable pipeline impact")

    if not notes:
        notes.append("Limited competitive context available — lead with value proposition and discovery questions")

    return notes

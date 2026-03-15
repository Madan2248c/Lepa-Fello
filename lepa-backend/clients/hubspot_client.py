"""
HubSpot CRM client.

Creates or updates a Company object in HubSpot with account intelligence
fields from the LEPA analysis pipeline.

Uses HubSpot's CRM Companies API (v3).
Docs: https://developers.hubspot.com/docs/api/crm/companies

Auth: Private App access token (HUBSPOT_ACCESS_TOKEN env var).
"""

import os
from typing import Optional
from dataclasses import dataclass

import httpx

HUBSPOT_API_BASE = "https://api.hubapi.com"


@dataclass
class HubSpotSyncResult:
    """Result of a HubSpot sync attempt."""

    success: bool
    external_id: Optional[str] = None
    error: Optional[str] = None
    action: Optional[str] = None


async def upsert_company(
    company_name: str,
    domain: Optional[str],
    industry: Optional[str],
    headquarters: Optional[str],
    company_size: Optional[str],
    ai_summary: str,
    intent_score: float,
    intent_stage: str,
    recommended_action: str,
    persona_label: str,
    overall_confidence: float,
    token: Optional[str] = None,
) -> HubSpotSyncResult:
    """
    Create or update a HubSpot Company record with LEPA intelligence.

    Searches for an existing company by domain first. If found, updates it.
    If not found, creates a new record.

    Standard HubSpot company properties used:
    - name, domain, industry, city, numberofemployees
    Custom properties (created as needed):
    - lepa_intent_score, lepa_intent_stage, lepa_persona,
      lepa_ai_summary, lepa_recommended_action, lepa_confidence

    Args:
        company_name: Official company name.
        domain: Primary website domain.
        industry: Industry classification.
        headquarters: HQ location string.
        company_size: Employee range string (e.g., '51-200').
        ai_summary: AI-generated account summary.
        intent_score: Buying intent score 0-10.
        intent_stage: Funnel stage string.
        recommended_action: First recommended sales action.
        persona_label: Inferred visitor persona.
        overall_confidence: Overall confidence score 0-1.

    Returns:
        HubSpotSyncResult with success status and external record ID.
    """
    token = token or os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not token:
        return HubSpotSyncResult(success=False, error="No HubSpot token configured")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    properties = _build_properties(
        company_name=company_name,
        domain=domain,
        industry=industry,
        headquarters=headquarters,
        company_size=company_size,
        ai_summary=ai_summary,
        intent_score=intent_score,
        intent_stage=intent_stage,
        recommended_action=recommended_action,
        persona_label=persona_label,
        overall_confidence=overall_confidence,
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            existing_id = None
            if domain:
                existing_id = await _find_company_by_domain(client, headers, domain)

            if existing_id:
                response = await client.patch(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/companies/{existing_id}",
                    headers=headers,
                    json={"properties": properties},
                )
                response.raise_for_status()
                return HubSpotSyncResult(
                    success=True,
                    external_id=existing_id,
                    action="updated",
                )
            else:
                response = await client.post(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/companies",
                    headers=headers,
                    json={"properties": properties},
                )
                response.raise_for_status()
                data = response.json()
                return HubSpotSyncResult(
                    success=True,
                    external_id=str(data.get("id")),
                    action="created",
                )

    except httpx.HTTPStatusError as e:
        body = e.response.text[:300]
        return HubSpotSyncResult(
            success=False,
            error=f"HubSpot API error {e.response.status_code}: {body}",
        )
    except Exception as e:
        return HubSpotSyncResult(success=False, error=f"HubSpot sync failed: {str(e)[:200]}")


async def _find_company_by_domain(
    client: httpx.AsyncClient,
    headers: dict,
    domain: str,
) -> Optional[str]:
    """Search HubSpot for an existing company by domain. Returns the record ID if found."""
    clean = domain.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        response = await client.post(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/companies/search",
            headers=headers,
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {"propertyName": "domain", "operator": "EQ", "value": clean}
                        ]
                    }
                ],
                "limit": 1,
            },
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return str(results[0]["id"])
    except Exception:
        pass
    return None


def _build_properties(
    company_name: str,
    domain: Optional[str],
    industry: Optional[str],
    headquarters: Optional[str],
    company_size: Optional[str],
    ai_summary: str,
    intent_score: float,
    intent_stage: str,
    recommended_action: str,
    persona_label: str,
    overall_confidence: float,
) -> dict:
    """Build the HubSpot properties payload."""
    props: dict = {"name": company_name}

    if domain:
        props["domain"] = domain.replace("https://", "").replace("http://", "").split("/")[0]
    # HubSpot's `industry` field only accepts values from a fixed picklist.
    # We skip it to avoid 400 errors — industry is included in the description block instead.
    if headquarters:
        city = headquarters.split(",")[0].strip()
        props["city"] = city[:50]
    if company_size:
        try:
            low = int(company_size.split("-")[0].replace("+", "").strip())
            props["numberofemployees"] = low
        except (ValueError, IndexError):
            pass

    # Pack all LEPA intelligence into the standard `description` field.
    # Custom lepa_* properties require manual creation in HubSpot first,
    # so we avoid them to keep the integration zero-setup.
    intelligence_block = (
        f"=== LEPA Account Intelligence ===\n"
        f"Intent: {intent_stage} (score {round(intent_score, 1)}/10)\n"
        f"Persona: {persona_label}\n"
        f"Confidence: {round(overall_confidence * 100)}%\n"
        f"Recommended Action: {recommended_action[:300] if recommended_action else 'N/A'}\n\n"
        f"AI Summary:\n{ai_summary[:600] if ai_summary else ''}"
    )
    props["description"] = intelligence_block[:1000]

    return props


# ── HubSpot Contacts API ──────────────────────────────────────────────────────

async def upsert_contact(
    name: str,
    title: Optional[str],
    company_name: str,
    company_domain: str,
    linkedin_url: Optional[str],
    role: Optional[str],
    headline: Optional[str],
    about: Optional[str],
    token: Optional[str] = None,
) -> HubSpotSyncResult:
    """Create or update a HubSpot Contact record."""
    token = token or os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not token:
        return HubSpotSyncResult(success=False, error="No HubSpot token configured")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    parts = name.strip().split(" ", 1)
    firstname = parts[0]
    lastname = parts[1] if len(parts) > 1 else ""

    notes = f"Role: {role or 'Unknown'}"
    if headline:
        notes += f"\nHeadline: {headline}"
    if about:
        notes += f"\nAbout: {about[:400]}"

    properties = {
        "firstname": firstname,
        "lastname": lastname,
        "jobtitle": title or "",
        "company": company_name,
        "hs_linkedin_url": linkedin_url or "",
        "message": notes[:1000],
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search by LinkedIn URL or name+company
            existing_id = await _find_contact(client, headers, linkedin_url, firstname, lastname, company_name)

            if existing_id:
                resp = await client.patch(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{existing_id}",
                    headers=headers, json={"properties": properties},
                )
                resp.raise_for_status()
                return HubSpotSyncResult(success=True, external_id=existing_id, action="updated")
            else:
                resp = await client.post(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts",
                    headers=headers, json={"properties": properties},
                )
                resp.raise_for_status()
                return HubSpotSyncResult(success=True, external_id=str(resp.json().get("id")), action="created")

    except httpx.HTTPStatusError as e:
        return HubSpotSyncResult(success=False, error=f"HubSpot {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        return HubSpotSyncResult(success=False, error=str(e)[:200])


async def _find_contact(client, headers, linkedin_url, firstname, lastname, company) -> Optional[str]:
    filters = []
    if linkedin_url:
        filters.append({"propertyName": "hs_linkedin_url", "operator": "EQ", "value": linkedin_url})
    else:
        filters = [
            {"propertyName": "firstname", "operator": "EQ", "value": firstname},
            {"propertyName": "lastname", "operator": "EQ", "value": lastname},
            {"propertyName": "company", "operator": "EQ", "value": company},
        ]
    try:
        resp = await client.post(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/search",
            headers=headers,
            json={"filterGroups": [{"filters": filters}], "limit": 1},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return str(results[0]["id"]) if results else None
    except Exception:
        return None

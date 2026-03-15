"""Contacts API — centralized buying committee repository."""

import logging
from typing import Optional
from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

logger = logging.getLogger("lepa.api.contacts")
router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("")
async def get_contacts(
    limit: int = Query(default=200, le=500),
    search: str | None = Query(default=None),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import list_contacts
    contacts = await list_contacts(tenant_id, limit, search=search)
    return {
        "total": len(contacts),
        "contacts": [_serialize(c) for c in contacts],
    }


class EnrichRequest(BaseModel):
    sender_name: str = ""


@router.post("/{contact_id}/enrich")
async def enrich_contact(
    contact_id: int,
    body: EnrichRequest = EnrichRequest(),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    """Generate personalized outreach (scrape LinkedIn only if not already cached)."""
    tenant_id = x_tenant_id or "default"
    from clients.db_client import get_contact, update_contact_linkedin, get_business_profile

    contact = await get_contact(tenant_id, contact_id)
    if not contact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Contact not found")

    # Use cached LinkedIn data if already scraped, otherwise scrape
    if contact.get("linkedin_scraped_at"):
        headline = contact.get("linkedin_headline") or ""
        about = contact.get("linkedin_about") or ""
        skills = contact.get("linkedin_skills") or []
        location = contact.get("linkedin_location") or ""
    else:
        headline, about, skills, location = "", "", [], ""
        if contact.get("source_url"):
            try:
                from clients.apify_linkedin_person_client import scrape_linkedin_persons
                profiles = await scrape_linkedin_persons([contact["source_url"]])
                if profiles and profiles[0].success:
                    p = profiles[0]
                    headline = p.headline or ""
                    about = p.about or ""
                    skills = p.skills[:10] if p.skills else []
                    location = p.location or ""
            except Exception as e:
                logger.warning(f"LinkedIn scrape failed: {e}")

    business_profile = await get_business_profile(tenant_id) or {}
    personalized_email, personalized_linkedin_msg = await _generate_outreach(
        contact, headline, about, business_profile, sender_name=body.sender_name
    )

    await update_contact_linkedin(
        tenant_id, contact_id, headline, about, skills, location,
        personalized_email, personalized_linkedin_msg
    )

    updated = await get_contact(tenant_id, contact_id)
    return _serialize(updated)


@router.post("/{contact_id}/push-hubspot")
async def push_to_hubspot(
    contact_id: int,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    """Push a single contact to HubSpot."""
    tenant_id = x_tenant_id or "default"
    from clients.db_client import get_contact, update_contact_hubspot
    from clients.hubspot_client import upsert_contact
    from api.routes_hubspot_connection import get_hs_token

    contact = await get_contact(tenant_id, contact_id)
    if not contact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Contact not found")

    result = await upsert_contact(
        name=contact["name"],
        title=contact.get("title"),
        company_name=contact.get("company_name", ""),
        company_domain=contact.get("company_domain", ""),
        linkedin_url=contact.get("source_url"),
        role=contact.get("role"),
        headline=contact.get("linkedin_headline"),
        about=contact.get("linkedin_about"),
        token=await get_hs_token(tenant_id),
    )

    if result.success and result.external_id:
        await update_contact_hubspot(tenant_id, contact_id, result.external_id)

    return {"success": result.success, "hubspot_id": result.external_id, "action": result.action, "error": result.error}


class BulkPushRequest(BaseModel):
    contact_ids: list[int]


@router.post("/bulk-push-hubspot")
async def bulk_push_hubspot(
    body: BulkPushRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    """Push multiple contacts to HubSpot."""
    tenant_id = x_tenant_id or "default"
    from clients.db_client import get_contact, update_contact_hubspot
    from clients.hubspot_client import upsert_contact
    from api.routes_hubspot_connection import get_hs_token
    import asyncio

    hs_token = await get_hs_token(tenant_id)

    async def push_one(contact_id: int):
        contact = await get_contact(tenant_id, contact_id)
        if not contact:
            return {"contact_id": contact_id, "success": False, "error": "Not found"}
        result = await upsert_contact(
            name=contact["name"], title=contact.get("title"),
            company_name=contact.get("company_name", ""), company_domain=contact.get("company_domain", ""),
            linkedin_url=contact.get("source_url"), role=contact.get("role"),
            headline=contact.get("linkedin_headline"), about=contact.get("linkedin_about"),
            token=hs_token,
        )
        if result.success and result.external_id:
            await update_contact_hubspot(tenant_id, contact_id, result.external_id)
        return {"contact_id": contact_id, "success": result.success, "hubspot_id": result.external_id, "error": result.error}

    results = await asyncio.gather(*[push_one(cid) for cid in body.contact_ids])
    return {"results": list(results), "pushed": sum(1 for r in results if r["success"])}


async def _generate_outreach(contact: dict, headline: str, about: str, business_profile: dict, sender_name: str = "") -> tuple[str, str]:
    """Generate personalized email and LinkedIn message using Claude."""
    try:
        from clients.bedrock_client import invoke_haiku
        import json

        seller = ""
        if sender_name:
            seller += f"Sender Name: {sender_name}\n"
        if business_profile.get("business_name"):
            seller += f"Seller: {business_profile['business_name']}\n"
        if business_profile.get("product_service"):
            seller += f"Product: {business_profile['product_service']}\n"
        if business_profile.get("value_proposition"):
            seller += f"Value Prop: {business_profile['value_proposition']}\n"

        prompt = f"""Generate personalized outreach for this contact.

CONTACT:
Name: {contact['name']}
Title: {contact.get('title', '')}
Role: {contact.get('role', '')}
Company: {contact.get('company_name', '')}
LinkedIn Headline: {headline}
About: {about[:300] if about else ''}

{seller}

Respond ONLY with JSON:
{{
  "email": "full personalized cold email (subject line + body, under 200 words)",
  "linkedin_msg": "personalized LinkedIn connection message (under 300 chars)"
}}"""

        response = await invoke_haiku(prompt=prompt, max_tokens=600, temperature=0.4)
        if response:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end])
            email_val = data.get("email", "")
            # Handle case where model returns email as {"subject": ..., "body": ...}
            if isinstance(email_val, dict):
                subj = email_val.get("subject", "")
                body = email_val.get("body", "")
                email_val = f"Subject: {subj}\n\n{body}" if subj else body
            return email_val, data.get("linkedin_msg", "")
    except Exception as e:
        logger.warning(f"Outreach generation failed: {e}")

    # Fallback
    email = f"Hi {contact['name'].split()[0]},\n\nI noticed your role as {contact.get('title', 'a leader')} at {contact.get('company_name', 'your company')} and wanted to reach out.\n\nWould love to connect and share how we can help.\n\nBest,"
    linkedin_msg = f"Hi {contact['name'].split()[0]}, I came across your profile and would love to connect regarding {contact.get('company_name', 'your company')}."
    return email, linkedin_msg


def _serialize(c: dict) -> dict:
    return {
        **{k: v for k, v in c.items() if k not in ("created_at", "linkedin_scraped_at", "hubspot_synced_at")},
        "created_at": c["created_at"].isoformat() if c.get("created_at") else None,
        "linkedin_scraped_at": c["linkedin_scraped_at"].isoformat() if c.get("linkedin_scraped_at") else None,
        "hubspot_synced_at": c["hubspot_synced_at"].isoformat() if c.get("hubspot_synced_at") else None,
        "linkedin_skills": list(c.get("linkedin_skills") or []),
    }

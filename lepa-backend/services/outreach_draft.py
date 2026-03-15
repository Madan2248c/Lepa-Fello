"""
Outreach draft generation service.

Generates personalized, signal-driven outreach drafts:
- Cold email (subject + body)
- LinkedIn connection message

Uses Claude to synthesize account intelligence into ready-to-send copy.
"""

import logging
from typing import Optional

from clients.bedrock_client import invoke_claude
from schemas.output_models import PersonaResult, IntentResult
from schemas.internal_models import CompanyProfile

logger = logging.getLogger("lepa.outreach_draft")

OUTREACH_PROMPT = """You are an expert B2B sales copywriter. Generate personalized outreach drafts based on account intelligence.

ACCOUNT INTELLIGENCE:
Company: {company_name}
Industry: {industry}
Size: {company_size}
Intent Stage: {intent_stage} (score: {intent_score}/10)
Persona: {persona_label}
Key Signals: {key_signals}
Business Signals: {business_signals}
Tech Stack: {tech_stack}
AI Summary: {ai_summary}

Generate TWO outreach drafts:

1. COLD EMAIL — subject line + 3-paragraph body (max 150 words total). Reference a specific signal. End with one clear CTA.
2. LINKEDIN MESSAGE — max 300 characters. Conversational, not salesy. Reference something specific about them.

Format your response EXACTLY as:

EMAIL_SUBJECT: <subject line>
EMAIL_BODY:
<email body>

LINKEDIN_MESSAGE:
<linkedin message>"""


async def generate_outreach_drafts(
    profile: CompanyProfile,
    persona: PersonaResult,
    intent: IntentResult,
    key_signals: list[str],
    business_signals_summary: list[str],
    tech_stack_names: list[str],
    ai_summary: str,
) -> dict:
    """
    Generate personalized outreach drafts for the top contact at this account.

    Returns:
        Dict with 'email_subject', 'email_body', 'linkedin_message', 'personalization_hooks'
    """
    if not profile.name or profile.name in ("Unknown Company", "Unknown Visitor"):
        return _default_drafts()

    prompt = OUTREACH_PROMPT.format(
        company_name=profile.name,
        industry=profile.industry or "Unknown",
        company_size=profile.company_size or "Unknown",
        intent_stage=intent.stage,
        intent_score=round(intent.score, 1),
        persona_label=persona.label,
        key_signals="; ".join(key_signals[:5]) or "None",
        business_signals="; ".join(business_signals_summary[:3]) or "None",
        tech_stack=", ".join(tech_stack_names[:6]) or "Unknown",
        ai_summary=ai_summary[:400],
    )

    try:
        raw = await invoke_claude(
            prompt=prompt,
            model="haiku",
            max_tokens=600,
        )
        return _parse_outreach_response(raw, profile.name)
    except Exception as e:
        logger.warning(f"Outreach draft generation failed: {e}")
        return _default_drafts()


def _parse_outreach_response(raw: str, company_name: str) -> dict:
    """Parse the structured outreach response from Claude."""
    result = {
        "email_subject": "",
        "email_body": "",
        "linkedin_message": "",
        "personalization_hooks": [],
    }

    lines = raw.strip().split("\n")
    current_section = None
    buffer = []

    for line in lines:
        if line.startswith("EMAIL_SUBJECT:"):
            result["email_subject"] = line.replace("EMAIL_SUBJECT:", "").strip()
        elif line.startswith("EMAIL_BODY:"):
            if current_section and buffer:
                result[current_section] = "\n".join(buffer).strip()
            current_section = "email_body"
            buffer = []
        elif line.startswith("LINKEDIN_MESSAGE:"):
            if current_section and buffer:
                result[current_section] = "\n".join(buffer).strip()
            current_section = "linkedin_message"
            buffer = []
        elif current_section:
            buffer.append(line)

    if current_section and buffer:
        result[current_section] = "\n".join(buffer).strip()

    # Extract personalization hooks (lines that reference specific signals)
    hooks = []
    for text in [result["email_body"], result["linkedin_message"]]:
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in ["hiring", "funding", "raised", "launched", "expanded", "congrat"]):
                hooks.append(line.strip())
    result["personalization_hooks"] = hooks[:3]

    return result


def _default_drafts() -> dict:
    return {
        "email_subject": "",
        "email_body": "",
        "linkedin_message": "",
        "personalization_hooks": [],
    }

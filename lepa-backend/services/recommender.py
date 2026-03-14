"""
AI-powered sales recommendation engine using Claude 3.5 Haiku.

Generates specific, actionable sales recommendations based on
account intelligence, persona, and intent signals.
"""

import json
from typing import Literal, Optional

from schemas.internal_models import CompanyProfile
from schemas.output_models import PersonaResult, IntentResult, RecommendedSalesAction
from clients.bedrock_client import invoke_haiku


RECOMMENDER_SYSTEM_PROMPT = """You are a B2B sales strategy expert. Generate specific, actionable recommendations for sales teams.

OUTPUT FORMAT - You MUST respond with ONLY valid JSON in this exact structure:
{
    "priority": "high" | "medium" | "low",
    "actions": ["specific action 1", "specific action 2", "specific action 3"],
    "outreach_angle": "One sentence describing the recommended messaging approach"
}

RULES:
1. Actions must be SPECIFIC and ACTIONABLE (e.g., "Send case study about [industry] ROI" not "Send relevant content")
2. Priority must match intent: Decision/Evaluation=high, Research=medium, Awareness=low
3. Tailor actions to the persona type (technical vs business buyer)
4. Reference specific company/industry details when available
5. Maximum 3 actions, each under 100 characters
6. Outreach angle should reference a specific pain point or value prop

DO NOT include any text outside the JSON object."""


async def generate_recommendations(
    profile: CompanyProfile,
    persona: PersonaResult,
    intent: IntentResult,
) -> RecommendedSalesAction:
    """
    Generate AI-powered sales recommendations.
    
    Uses Claude 3.5 Haiku for fast, cost-effective inference.
    Falls back to rule-based recommendations if AI fails.
    
    Args:
        profile: Enriched company profile.
        persona: Inferred visitor persona.
        intent: Intent score and stage.
        
    Returns:
        RecommendedSalesAction with priority, actions, and outreach angle.
    """
    prompt = _build_recommendation_prompt(profile, persona, intent)

    ai_response = await invoke_haiku(
        prompt=prompt,
        system_prompt=RECOMMENDER_SYSTEM_PROMPT,
        max_tokens=400,
        temperature=0.3,
    )

    if ai_response:
        parsed = _parse_ai_recommendation(ai_response)
        if parsed:
            return parsed

    return _generate_rule_based_recommendations(profile, persona, intent)


def _build_recommendation_prompt(
    profile: CompanyProfile,
    persona: PersonaResult,
    intent: IntentResult,
) -> str:
    """Build prompt for recommendation generation."""
    
    company_context = []
    company_context.append(f"Company: {profile.name}")
    if profile.industry:
        company_context.append(f"Industry: {profile.industry}")
    if profile.company_size:
        company_context.append(f"Size: {profile.company_size} employees")
    if profile.headquarters:
        company_context.append(f"Location: {profile.headquarters}")
    
    return f"""Generate sales recommendations for this account:

COMPANY:
{chr(10).join(company_context)}

VISITOR PROFILE:
- Persona: {persona.label} ({persona.confidence:.0%} confidence)
- Key behaviors: {', '.join(persona.reasons[:2]) if persona.reasons else 'None observed'}

INTENT:
- Score: {intent.score}/10
- Stage: {intent.stage}
- Signals: {', '.join(intent.reasons[:2]) if intent.reasons else 'None'}

Generate specific, actionable recommendations as JSON."""


def _parse_ai_recommendation(response: str) -> Optional[RecommendedSalesAction]:
    """Parse AI response into structured recommendation."""
    try:
        response = response.strip()
        
        start = response.find("{")
        end = response.rfind("}") + 1
        
        if start < 0 or end <= start:
            return None
            
        json_str = response[start:end]
        data = json.loads(json_str)

        priority = data.get("priority", "medium").lower()
        if priority not in ("high", "medium", "low"):
            priority = "medium"

        actions = data.get("actions", [])
        if isinstance(actions, str):
            actions = [actions]
        elif not isinstance(actions, list):
            actions = []
        
        actions = [str(a).strip() for a in actions if a][:5]
        
        if not actions:
            return None

        outreach_angle = data.get("outreach_angle", "")
        if not outreach_angle or not isinstance(outreach_angle, str):
            outreach_angle = "Personalize based on observed behavior and company context."

        return RecommendedSalesAction(
            priority=priority,
            actions=actions,
            outreach_angle=str(outreach_angle).strip(),
        )
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Failed to parse AI recommendation: {e}")
        return None


def _generate_rule_based_recommendations(
    profile: CompanyProfile,
    persona: PersonaResult,
    intent: IntentResult,
) -> RecommendedSalesAction:
    """Generate recommendations using rule-based logic when AI fails."""
    
    industry_mention = f" in {profile.industry}" if profile.industry else ""
    company_mention = profile.name if profile.name != "Unknown Company" else "this account"
    
    if intent.stage == "Decision":
        actions = [
            f"Reach out to {company_mention} within 24 hours - high buying intent detected",
            "Prepare a customized demo or POC proposal",
            f"Share pricing options with relevant case studies{industry_mention}",
        ]
        angle = f"Lead with urgency and social proof from similar companies{industry_mention}. They're ready to buy."
        
        return RecommendedSalesAction(
            priority="high",
            actions=actions,
            outreach_angle=angle,
        )

    if intent.stage == "Evaluation":
        if persona.label == "Technical Evaluator":
            actions = [
                f"Add {company_mention} to high-priority technical sequence",
                "Share technical documentation, API guides, and integration examples",
                f"Offer a technical deep-dive call with solutions engineer",
            ]
            angle = "Lead with technical capabilities, ease of integration, and developer experience."
        else:
            actions = [
                f"Add {company_mention} to evaluation-stage outbound sequence",
                f"Share ROI case study from {profile.industry or 'similar'} customer",
                "Connect with likely decision-maker on LinkedIn",
            ]
            angle = f"Focus on business outcomes and ROI{industry_mention}. Reference their evaluation activity."
        
        return RecommendedSalesAction(
            priority="high",
            actions=actions,
            outreach_angle=angle,
        )

    if intent.stage == "Research":
        actions = [
            f"Add {company_mention} to educational nurture campaign",
            "Send thought leadership content relevant to their browsing topics",
            "Monitor for return visits or increased engagement",
        ]
        angle = "Provide value first - share insights about challenges they may be researching."
        
        return RecommendedSalesAction(
            priority="medium",
            actions=actions,
            outreach_angle=angle,
        )

    actions = [
        f"Add {company_mention} to awareness campaign",
        "Monitor for return visits or increased activity",
        "Include in general marketing nurture flow",
    ]
    
    return RecommendedSalesAction(
        priority="low",
        actions=actions,
        outreach_angle="Soft touch approach - build brand awareness without aggressive sales messaging.",
    )

"""
AI-powered account summary generation using Claude 4 Sonnet.

This module generates concise, actionable account intelligence summaries
by synthesizing company profile, visitor behavior, and intent signals.
"""

import os
from typing import Optional

from strands import Agent
from strands.models import BedrockModel

from schemas.internal_models import CompanyProfile
from schemas.output_models import PersonaResult, IntentResult
from clients.bedrock_client import (
    invoke_sonnet,
    get_boto_session,
    CLAUDE_SONNET_MODEL_ID,
)


SUMMARIZER_SYSTEM_PROMPT = """You are a senior B2B sales intelligence analyst. Your job is to generate concise, actionable account summaries for sales teams.

CRITICAL RULES:
1. Be specific - use actual data points, not vague statements
2. Be concise - 2-3 sentences maximum
3. Be actionable - focus on what makes this account worth pursuing
4. Be honest about confidence - if data is limited, say so
5. Never fabricate information - only use what's provided

STRUCTURE:
- Lead with the most important insight about the account
- Include relevant behavioral signals if available
- End with why this account matters for sales

AVOID:
- Generic statements like "shows potential interest"
- Restating obvious facts without insight
- Marketing buzzwords and fluff
- Speculation beyond the evidence"""


async def generate_ai_summary(
    profile: CompanyProfile,
    persona: PersonaResult,
    intent: IntentResult,
    key_signals: list[str],
) -> str:
    """
    Generate an AI-powered account intelligence summary.
    
    Uses Claude 4 Sonnet for high-quality synthesis.
    Falls back to deterministic template if AI fails.
    
    Args:
        profile: Enriched company profile data.
        persona: Inferred visitor persona with confidence.
        intent: Intent score and stage.
        key_signals: List of observed behavioral signals.
        
    Returns:
        2-3 sentence human-readable account summary.
    """
    prompt = _build_summary_prompt(profile, persona, intent, key_signals)

    ai_summary = await invoke_sonnet(
        prompt=prompt,
        system_prompt=SUMMARIZER_SYSTEM_PROMPT,
        max_tokens=300,
        temperature=0.4,
    )

    if ai_summary and len(ai_summary.strip()) > 30:
        cleaned = ai_summary.strip()
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        return cleaned

    return _generate_template_summary(profile, persona, intent, key_signals)


def _build_summary_prompt(
    profile: CompanyProfile,
    persona: PersonaResult,
    intent: IntentResult,
    key_signals: list[str],
) -> str:
    """Build the prompt for AI summary generation."""
    
    company_facts = []
    company_facts.append(f"Company: {profile.name}")
    if profile.industry:
        company_facts.append(f"Industry: {profile.industry}")
    if profile.company_size:
        company_facts.append(f"Size: {profile.company_size} employees")
    if profile.headquarters:
        company_facts.append(f"Location: {profile.headquarters}")
    if profile.description:
        company_facts.append(f"Business: {profile.description[:200]}")
    
    behavior_facts = []
    behavior_facts.append(f"Visitor Persona: {persona.label} ({persona.confidence:.0%} confidence)")
    if persona.reasons:
        behavior_facts.append(f"Persona evidence: {'; '.join(persona.reasons[:2])}")
    behavior_facts.append(f"Intent Score: {intent.score}/10 ({intent.stage} stage)")
    if intent.reasons:
        behavior_facts.append(f"Intent signals: {'; '.join(intent.reasons[:3])}")
    
    signals_section = ""
    if key_signals:
        signals_section = f"\nKey Observations:\n- " + "\n- ".join(key_signals[:5])

    return f"""Generate a 2-3 sentence sales intelligence summary for this account.

COMPANY DATA:
{chr(10).join(company_facts)}

BEHAVIORAL DATA:
{chr(10).join(behavior_facts)}
{signals_section}

DATA CONFIDENCE: {profile.confidence:.0%}

Write a brief, insight-driven summary. Focus on actionable intelligence, not just facts. Output only the summary, nothing else."""


def _generate_template_summary(
    profile: CompanyProfile,
    persona: PersonaResult,
    intent: IntentResult,
    key_signals: list[str],
) -> str:
    """Generate a deterministic fallback summary when AI fails."""
    
    name = profile.name
    
    size_desc = ""
    if profile.company_size:
        if profile.company_size in ["1-10", "11-50"]:
            size_desc = "small"
        elif profile.company_size in ["51-200", "201-500"]:
            size_desc = "mid-sized"
        else:
            size_desc = "large"
    
    industry_desc = profile.industry.lower() if profile.industry else "technology"
    
    if intent.stage == "Decision":
        urgency = "showing strong buying signals and is likely in final evaluation"
        priority = "This is a high-priority account requiring immediate attention."
    elif intent.stage == "Evaluation":
        urgency = "actively evaluating solutions with moderate-to-high intent"
        priority = "Consider prioritizing outreach with relevant proof points."
    elif intent.stage == "Research":
        urgency = "in early research phase, gathering information"
        priority = "A nurture approach with educational content is recommended."
    else:
        urgency = "at early awareness stage"
        priority = "Add to awareness campaigns and monitor for increased engagement."
    
    if size_desc:
        opening = f"{name} is a {size_desc} {industry_desc} company {urgency}."
    else:
        opening = f"{name} operates in {industry_desc} and is {urgency}."
    
    if persona.label == "Business Buyer" and persona.confidence > 0.6:
        persona_insight = "Visitor behavior suggests a decision-maker evaluating business value."
    elif persona.label == "Technical Evaluator" and persona.confidence > 0.6:
        persona_insight = "Visitor behavior indicates technical evaluation in progress."
    elif key_signals:
        persona_insight = f"Notable activity: {key_signals[0].lower()}."
    else:
        persona_insight = ""
    
    parts = [opening]
    if persona_insight:
        parts.append(persona_insight)
    parts.append(priority)
    
    return " ".join(parts)

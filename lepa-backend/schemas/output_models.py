from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class PersonaResult(BaseModel):
    """Inferred visitor persona with confidence and reasoning."""

    label: str = Field(..., description="Persona label (e.g., 'Business Buyer', 'Technical Evaluator')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasons: list[str] = Field(default_factory=list, description="Evidence supporting this persona")


class IntentResult(BaseModel):
    """Buying intent score with funnel stage and reasoning."""

    score: float = Field(..., ge=0.0, le=10.0, description="Intent score 0-10")
    stage: Literal["Awareness", "Research", "Evaluation", "Decision"] = Field(
        ..., description="Funnel stage based on score"
    )
    reasons: list[str] = Field(default_factory=list, description="Signals contributing to the score")


class RecommendedSalesAction(BaseModel):
    """AI-generated sales recommendation."""

    priority: Literal["high", "medium", "low"] = Field(..., description="Action urgency")
    actions: list[str] = Field(default_factory=list, description="Specific next steps")
    outreach_angle: str = Field(..., description="Suggested messaging angle")


class TechStackItem(BaseModel):
    """A single detected technology."""

    category: Literal["crm", "marketing_automation", "cms", "analytics", "payments", "support", "devtools", "hosting", "other"]
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: Literal["builtwith", "page_scan", "other"] = "other"


class BusinessSignal(BaseModel):
    """A public business signal (hiring, funding, expansion, etc.)."""

    type: Literal["hiring", "funding", "expansion", "product_launch", "other"]
    summary: str
    published_at: Optional[str] = Field(None, description="ISO-8601 date or null")
    source_url: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class LeadershipContact(BaseModel):
    """A likely decision-maker discovered from public sources."""

    name: str
    title: str
    source_url: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class EnrichmentEvidence(BaseModel):
    """Source evidence collected during Phase 2 enrichment."""

    website_pages: list[str] = Field(default_factory=list)
    news_links: list[str] = Field(default_factory=list)
    technology_sources: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """Complete analysis response — Phase 1 + Phase 2 enrichment fields."""

    input_type: Literal["visitor_signal", "company_seed"] = Field(
        ..., description="Which input path was used"
    )
    input_id: str = Field(..., description="ID of the input (visitor_id or company_name)")

    account_name: Optional[str] = Field(None, description="Resolved company/account name")
    domain: Optional[str] = Field(None, description="Company website domain")
    industry: Optional[str] = Field(None, description="Industry classification")
    headquarters: Optional[str] = Field(None, description="Company HQ location")
    company_size: Optional[str] = Field(None, description="Employee count range")
    founded_year: Optional[str] = Field(None, description="Year company was founded")
    business_description: Optional[str] = Field(None, description="Brief company description")

    persona: PersonaResult = Field(..., description="Inferred visitor persona")
    intent: IntentResult = Field(..., description="Buying intent assessment")

    technology_stack: list[TechStackItem] = Field(
        default_factory=list, description="Detected technologies used by the company"
    )
    business_signals: list[BusinessSignal] = Field(
        default_factory=list, description="Public business signals (hiring, funding, etc.)"
    )
    leadership: list[LeadershipContact] = Field(
        default_factory=list, description="Likely decision-makers from public sources"
    )

    key_signals_observed: list[str] = Field(
        default_factory=list, description="Notable behavioral signals"
    )
    ai_summary: str = Field(..., description="AI-generated account intelligence summary")
    recommended_sales_action: RecommendedSalesAction = Field(
        ..., description="Next-step sales recommendation"
    )

    overall_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence in the analysis"
    )
    source_links: list[str] = Field(
        default_factory=list, description="URLs used as data sources"
    )
    evidence: EnrichmentEvidence = Field(
        default_factory=EnrichmentEvidence, description="Structured evidence from Phase 2 enrichment"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of analysis"
    )

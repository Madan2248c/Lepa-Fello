from typing import Optional, Literal, Any
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


class BuyingCommitteeMember(BaseModel):
    """A member of the buying committee with role classification and optional LinkedIn enrichment."""

    name: str
    title: str
    role: str = Field(..., description="Economic Buyer | Champion | Technical Evaluator | End User | Blocker | Influencer")
    rationale: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_url: Optional[str] = None
    linkedin_profile: Optional[dict] = Field(None, description="Enriched LinkedIn person profile data")


class TrendVelocity(BaseModel):
    """Signal velocity / surge detection for a company."""

    status: Literal["surging", "stable", "declining", "unknown"]
    recent_signal_count: int = 0
    baseline_signal_count: int = 0
    velocity_ratio: float = 0.0
    surge_topics: list[str] = Field(default_factory=list)
    interpretation: str = ""


class OutreachDraft(BaseModel):
    """AI-generated personalized outreach drafts."""

    email_subject: str = ""
    email_body: str = ""
    linkedin_message: str = ""
    personalization_hooks: list[str] = Field(default_factory=list)


class IcpFitScore(BaseModel):
    """ICP fit scoring with dimension breakdown."""

    overall_score: int = Field(..., ge=0, le=100, description="0-100 ICP fit score")
    tier: Literal["Strong Fit", "Good Fit", "Partial Fit", "Poor Fit"]
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    fit_reasons: list[str] = Field(default_factory=list)
    gap_reasons: list[str] = Field(default_factory=list)


class CompetitiveContext(BaseModel):
    """Competitive intelligence for sales positioning."""

    current_vendors: list[str] = Field(default_factory=list)
    competitor_categories: dict[str, list[str]] = Field(default_factory=dict)
    competitive_mentions: list[str] = Field(default_factory=list)
    displacement_opportunities: list[dict] = Field(default_factory=list)
    positioning_notes: list[str] = Field(default_factory=list)


class PipelineStep(BaseModel):
    """A single step in the enrichment pipeline trace."""
    step: str
    source: str
    status: Literal["success", "partial", "failed", "skipped"]
    duration_ms: Optional[int] = None
    records_found: Optional[int] = None
    note: str = ""


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

    # Phase 3: Advanced intelligence features
    buying_committee: list[BuyingCommitteeMember] = Field(
        default_factory=list, description="Buying committee with role classification and LinkedIn enrichment"
    )
    trend_velocity: Optional[TrendVelocity] = Field(
        None, description="Signal surge/velocity detection"
    )
    outreach_draft: Optional[OutreachDraft] = Field(
        None, description="AI-generated personalized outreach drafts"
    )
    icp_fit: Optional[IcpFitScore] = Field(
        None, description="ICP fit score with dimension breakdown"
    )
    competitive_context: Optional[CompetitiveContext] = Field(
        None, description="Competitive intelligence and positioning notes"
    )

    pipeline_trace: list[PipelineStep] = Field(
        default_factory=list, description="Enrichment pipeline execution trace for transparency"
    )

    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of analysis"
    )

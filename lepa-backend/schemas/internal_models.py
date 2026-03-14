from typing import Optional, Literal
from pydantic import BaseModel, Field


class IPInfoResult(BaseModel):
    """Result from IPInfo Lite API lookup."""

    ip: str
    asn: Optional[str] = None
    as_name: Optional[str] = None
    as_domain: Optional[str] = None
    country_code: Optional[str] = None
    country: Optional[str] = None
    continent_code: Optional[str] = None
    continent: Optional[str] = None


class CompanyCandidate(BaseModel):
    """Preliminary company identification from IP or seed input."""

    name: Optional[str] = Field(None, description="Best-guess company name")
    domain: Optional[str] = Field(None, description="Company domain if known")
    source: Literal["ip_lookup", "company_seed", "research_agent"] = Field(
        ..., description="How the candidate was identified"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the match")
    confidence_reasons: list[str] = Field(
        default_factory=list, description="Why confidence is high/low"
    )
    raw_ip_info: Optional[IPInfoResult] = Field(
        None, description="Raw IPInfo response if from IP lookup"
    )


class CompanyProfile(BaseModel):
    """Enriched company profile from research agent."""

    name: str = Field(..., description="Official company name")
    domain: Optional[str] = Field(None, description="Primary website domain")
    industry: Optional[str] = Field(None, description="Industry classification")
    headquarters: Optional[str] = Field(None, description="HQ city/region/country")
    company_size: Optional[str] = Field(None, description="Employee range (e.g., '51-200')")
    founded_year: Optional[str] = Field(None, description="Year founded")
    description: Optional[str] = Field(None, description="Business description")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn company page")
    
    source_links: list[str] = Field(
        default_factory=list, description="URLs used to gather this info"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Overall profile confidence"
    )


class VisitorContext(BaseModel):
    """Normalized visitor behavior context."""

    ip_address: Optional[str] = None
    pages_visited: list[str] = Field(default_factory=list)
    time_on_site_seconds: Optional[int] = None
    visits_this_week: Optional[int] = None
    referral_source: Optional[str] = None


class CompanySeed(BaseModel):
    """Normalized company seed input."""

    name: Optional[str] = None
    partial_domain: Optional[str] = None


class NormalizedAccountInput(BaseModel):
    """Unified internal representation for both input paths."""

    input_type: Literal["visitor_signal", "company_seed"]
    input_id: str = Field(..., description="visitor_id or company_name")
    raw_input: dict = Field(default_factory=dict, description="Original input preserved")

    company_seed: CompanySeed = Field(default_factory=CompanySeed)
    visitor_context: VisitorContext = Field(default_factory=VisitorContext)

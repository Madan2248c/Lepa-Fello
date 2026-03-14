from typing import Optional
from pydantic import BaseModel, Field


class VisitorSignalInput(BaseModel):
    """Input model for website visitor signal analysis."""

    visitor_id: str = Field(..., description="Unique identifier for the visitor session")
    ip_address: Optional[str] = Field(None, description="Visitor's IP address for company resolution")
    pages_visited: list[str] = Field(
        default_factory=list,
        description="List of page paths visited (e.g., ['/pricing', '/docs', '/case-studies'])",
    )
    time_on_site_seconds: Optional[int] = Field(
        None, ge=0, description="Total time spent on site in seconds"
    )
    visits_this_week: Optional[int] = Field(
        None, ge=0, description="Number of visits in the current week"
    )
    referral_source: Optional[str] = Field(
        None, description="Traffic source (e.g., 'google', 'linkedin', 'direct')"
    )
    device_metadata: Optional[dict] = Field(
        None, description="Device info (browser, OS, device type)"
    )
    location_metadata: Optional[dict] = Field(
        None, description="Geo location from client (city, region, country)"
    )


class CompanySeedInput(BaseModel):
    """Input model for company-name-based analysis."""

    company_name: str = Field(..., min_length=1, description="Name of the company to analyze")
    partial_domain: Optional[str] = Field(
        None, description="Optional partial or full domain hint (e.g., 'acme' or 'acme.com')"
    )

"""
Apollo.io API client for company and people enrichment.

Production-grade client with:
- Rate limiting awareness
- Retry logic with exponential backoff
- Comprehensive data extraction
- Error handling and logging
"""

import os
import asyncio
from typing import Optional
from dataclasses import dataclass, field

import httpx


APOLLO_BASE_URL = "https://api.apollo.io/api/v1"

MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0


@dataclass
class ApolloOrganization:
    """Organization data from Apollo.io API."""
    
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    estimated_num_employees: Optional[int] = None
    employee_range: Optional[str] = None
    headquarters: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    founded_year: Optional[int] = None
    description: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    facebook_url: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    phone: Optional[str] = None
    annual_revenue: Optional[str] = None
    annual_revenue_printed: Optional[str] = None
    technologies: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


def _get_employee_range(count: Optional[int]) -> Optional[str]:
    """Convert employee count to standardized range."""
    if not count:
        return None
    
    ranges = [
        (10, "1-10"),
        (50, "11-50"),
        (200, "51-200"),
        (500, "201-500"),
        (1000, "501-1000"),
        (5000, "1001-5000"),
        (10000, "5001-10000"),
    ]
    
    for threshold, label in ranges:
        if count < threshold:
            return label
    
    return "10000+"


def _build_headquarters(org: dict) -> Optional[str]:
    """Build headquarters string from Apollo org data."""
    parts = []
    
    if org.get("city"):
        parts.append(org["city"])
    if org.get("state"):
        parts.append(org["state"])
    if org.get("country"):
        parts.append(org["country"])
    
    return ", ".join(parts) if parts else None


async def enrich_organization(domain: str) -> ApolloOrganization:
    """
    Enrich organization data using Apollo.io API.
    
    Args:
        domain: Company domain (e.g., 'stripe.com')
        
    Returns:
        ApolloOrganization with enriched data
    """
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        return ApolloOrganization(error="APOLLO_API_KEY not configured")

    if not domain:
        return ApolloOrganization(error="No domain provided")

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    url = f"{APOLLO_BASE_URL}/organizations/enrich"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }
    params = {"domain": domain}

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 429:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    print(f"Apollo rate limited, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                response.raise_for_status()
                data = response.json()

            org = data.get("organization", {})
            if not org:
                return ApolloOrganization(
                    error="No organization data returned",
                    domain=domain,
                )

            description = org.get("short_description")
            if not description:
                description = org.get("seo_description")
            if not description:
                description = org.get("snippets_loaded")
            
            technologies = []
            if org.get("current_technologies"):
                technologies = [t.get("name") for t in org["current_technologies"] if t.get("name")]
            
            keywords = org.get("keywords", []) or []
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",")]

            return ApolloOrganization(
                name=org.get("name"),
                domain=org.get("primary_domain") or domain,
                industry=org.get("industry"),
                estimated_num_employees=org.get("estimated_num_employees"),
                employee_range=_get_employee_range(org.get("estimated_num_employees")),
                headquarters=_build_headquarters(org),
                city=org.get("city"),
                state=org.get("state"),
                country=org.get("country"),
                founded_year=org.get("founded_year"),
                description=description,
                linkedin_url=org.get("linkedin_url"),
                twitter_url=org.get("twitter_url"),
                facebook_url=org.get("facebook_url"),
                logo_url=org.get("logo_url"),
                website_url=org.get("website_url"),
                phone=org.get("phone"),
                annual_revenue=org.get("annual_revenue"),
                annual_revenue_printed=org.get("annual_revenue_printed"),
                technologies=technologies[:10],
                keywords=keywords[:10],
                success=True,
            )

        except httpx.HTTPStatusError as e:
            if attempt < MAX_RETRIES - 1 and e.response.status_code >= 500:
                await asyncio.sleep(RETRY_DELAY_BASE * (2 ** attempt))
                continue
            return ApolloOrganization(error=f"Apollo API error: HTTP {e.response.status_code}")
        
        except httpx.TimeoutException:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY_BASE)
                continue
            return ApolloOrganization(error="Apollo API timeout")
        
        except Exception as e:
            return ApolloOrganization(error=f"Apollo enrichment failed: {str(e)[:100]}")
    
    return ApolloOrganization(error="Apollo API failed after retries")


async def search_organization_by_name(company_name: str) -> Optional[str]:
    """
    Search Apollo for an organization by name and return its domain.
    
    Args:
        company_name: Company name to search for
        
    Returns:
        Primary domain if found, None otherwise
    """
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        return None

    if not company_name:
        return None

    url = f"{APOLLO_BASE_URL}/mixed_companies/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }
    payload = {
        "q_organization_name": company_name,
        "page": 1,
        "per_page": 5,
    }

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 429:
                    await asyncio.sleep(RETRY_DELAY_BASE * (2 ** attempt))
                    continue
                
                response.raise_for_status()
                data = response.json()

            organizations = data.get("organizations", [])
            
            if not organizations:
                return None
            
            name_lower = company_name.lower()
            for org in organizations:
                org_name = (org.get("name") or "").lower()
                if org_name == name_lower or name_lower in org_name:
                    return org.get("primary_domain")
            
            return organizations[0].get("primary_domain")

        except httpx.HTTPStatusError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY_BASE * (2 ** attempt))
                continue
            return None
        
        except Exception as e:
            print(f"Apollo search failed: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY_BASE)
                continue
            return None
    
    return None


async def search_people_at_company(
    domain: str,
    titles: Optional[list[str]] = None,
    limit: int = 5,
) -> list[dict]:
    """
    Search for people at a company (for leadership discovery).
    
    Args:
        domain: Company domain to search
        titles: Optional list of titles to filter by (e.g., ["CEO", "VP Sales"])
        limit: Maximum number of results
        
    Returns:
        List of person records with name, title, email, linkedin_url
    """
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        return []

    url = f"{APOLLO_BASE_URL}/mixed_people/api_search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }
    
    payload = {
        "q_organization_domains": domain,
        "page": 1,
        "per_page": limit,
    }
    
    if titles:
        payload["person_titles"] = titles

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        people = []
        for person in data.get("people", []):
            people.append({
                "name": person.get("name"),
                "title": person.get("title"),
                "email": person.get("email"),
                "linkedin_url": person.get("linkedin_url"),
                "phone": person.get("phone_numbers", [{}])[0].get("sanitized_number") if person.get("phone_numbers") else None,
            })
        
        return people

    except Exception as e:
        print(f"Apollo people search failed: {e}")
        return []

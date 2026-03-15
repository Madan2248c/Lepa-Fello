"""
Exa neural search client for business signals and leadership discovery.

Exa is a semantic search engine purpose-built for AI agents. It understands
natural language queries and returns full page content, making it ideal for:
- Finding recent news about a company (funding, hiring, expansion, launches)
- Discovering leadership/team pages with structured contact data
"""

import os
from typing import Optional
from dataclasses import dataclass, field

import httpx


EXA_API_BASE = "https://api.exa.ai"


@dataclass
class ExaResult:
    """A single result from an Exa search."""

    title: str
    url: str
    published_date: Optional[str] = None
    text: Optional[str] = None
    score: float = 0.0
    # People search extras
    person_name: Optional[str] = None
    person_title: Optional[str] = None
    person_company: Optional[str] = None

@dataclass
class ExaSearchResponse:
    """Response from an Exa search query."""

    results: list[ExaResult] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


async def search_business_signals_dated(
    company_name: str,
    domain: Optional[str] = None,
    num_results: int = 10,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
) -> ExaSearchResponse:
    """Search for business signals with optional date range filtering."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return ExaSearchResponse(success=False, error="EXA_API_KEY not configured")


async def search_people(
    query: str,
    num_results: int = 10,
) -> ExaSearchResponse:
    """
    Search for people using Exa's People Search (category='people').
    
    Returns LinkedIn profiles and other professional profiles.
    Example queries:
    - "Ivan Zhao CEO Notion"
    - "VP of Product at Microsoft"
    - "enterprise sales reps from Stripe"
    
    Args:
        query: Natural language query for people search
        num_results: Number of results to return
        
    Returns:
        ExaSearchResponse with LinkedIn profile URLs
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return ExaSearchResponse(success=False, error="EXA_API_KEY not configured")
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    
    payload = {
        "query": query,
        "category": "people",
        "numResults": num_results,
        "useAutoprompt": True,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{EXA_API_BASE}/search",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                # Extract structured person data from entities if available
                person_name = person_title_str = person_company = None
                entities = item.get("entities") or []
                if entities:
                    props = entities[0].get("properties", {})
                    person_name = props.get("name")
                    work = props.get("workHistory") or []
                    if work:
                        person_title_str = work[0].get("title")
                        co = work[0].get("company") or {}
                        person_company = co.get("name")

                results.append(
                    ExaResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        published_date=item.get("publishedDate"),
                        score=item.get("score", 0.0),
                        person_name=person_name,
                        person_title=person_title_str,
                        person_company=person_company,
                    )
                )
            
            return ExaSearchResponse(results=results, success=True)
    
    except Exception as e:
        return ExaSearchResponse(success=False, error=str(e))


async def search_business_signals_dated(
    company_name: str,
    domain: Optional[str] = None,
    num_results: int = 10,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
) -> ExaSearchResponse:
    """Search for business signals with optional date range filtering."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return ExaSearchResponse(success=False, error="EXA_API_KEY not configured")

    query = f"{company_name} company news funding hiring expansion product launch"
    return await _exa_search(
        api_key=api_key,
        query=query,
        num_results=num_results,
        include_text=False,
        use_autoprompt=True,
        exclude_domains=["linkedin.com", "facebook.com"],
        start_published_date=start_published_date,
        end_published_date=end_published_date,
    )


async def search_business_signals(
    company_name: str,
    domain: Optional[str] = None,
    num_results: int = 8,
) -> ExaSearchResponse:
    """
    Search for recent public business signals about a company.

    Queries for funding, hiring, expansion, and product launch news using
    Exa's neural search. Returns articles with full text for classification.

    Args:
        company_name: Name of the company to research.
        domain: Optional domain to anchor the search.
        num_results: Maximum number of results to return.

    Returns:
        ExaSearchResponse with matched articles.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return ExaSearchResponse(success=False, error="EXA_API_KEY not configured")

    company_ref = domain or company_name
    query = (
        f"{company_name} company news funding hiring expansion product launch 2024 2025"
    )

    return await _exa_search(
        api_key=api_key,
        query=query,
        num_results=num_results,
        include_text=True,
        use_autoprompt=True,
        exclude_domains=["linkedin.com", "facebook.com"],
    )


async def search_leadership(
    company_name: str,
    domain: Optional[str] = None,
    num_results: int = 5,
) -> ExaSearchResponse:
    """
    Search for leadership and team information about a company.

    Targets team pages, about pages, and executive profiles to find
    likely decision-makers.

    Args:
        company_name: Name of the company.
        domain: Optional domain to anchor the search.
        num_results: Maximum number of results to return.

    Returns:
        ExaSearchResponse with team/leadership pages.
    """
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return ExaSearchResponse(success=False, error="EXA_API_KEY not configured")

    query = f"{company_name} CEO founder leadership team executive management"

    include_domains = []
    if domain:
        clean = domain.replace("https://", "").replace("http://", "").split("/")[0]
        include_domains = [clean]

    return await _exa_search(
        api_key=api_key,
        query=query,
        num_results=num_results,
        include_text=True,
        use_autoprompt=False,
        include_domains=include_domains if include_domains else None,
    )


async def _exa_search(
    api_key: str,
    query: str,
    num_results: int,
    include_text: bool = True,
    use_autoprompt: bool = True,
    include_domains: Optional[list[str]] = None,
    exclude_domains: Optional[list[str]] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
) -> ExaSearchResponse:
    """
    Core Exa search call with text content retrieval.

    Uses Exa's /search endpoint with contents.text to get full page text
    in a single round-trip, avoiding a separate /contents call.
    """
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    payload: dict = {
        "query": query,
        "numResults": num_results,
        "useAutoprompt": use_autoprompt,
        "type": "neural",
        "contents": {
            "text": {"maxCharacters": 1500} if include_text else False,
        },
    }

    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains
    if start_published_date:
        payload["startPublishedDate"] = start_published_date
    if end_published_date:
        payload["endPublishedDate"] = end_published_date

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{EXA_API_BASE}/search",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", []):
            results.append(
                ExaResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    published_date=item.get("publishedDate"),
                    text=item.get("text"),
                    score=item.get("score") or 0.0,
                )
            )

        return ExaSearchResponse(results=results, success=True)

    except httpx.HTTPStatusError as e:
        return ExaSearchResponse(
            success=False,
            error=f"Exa API error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return ExaSearchResponse(success=False, error=f"Exa search failed: {str(e)[:150]}")

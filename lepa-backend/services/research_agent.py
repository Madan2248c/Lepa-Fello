"""
Production Research Agent using Strands Agents SDK.

This agent orchestrates company research using multiple tools:
- Web scraping for company websites
- Apollo.io API for enrichment

Uses Strands Agent with invoke_async for FastAPI compatibility.
Tool results are captured via a HookProvider to reliably extract
the compiled profile without parsing the agent's text output.
"""

import os
import httpx
from typing import Optional, Any

from strands import Agent, tool
from strands.models import BedrockModel
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterToolCallEvent

from schemas.internal_models import CompanyCandidate, CompanyProfile
from clients.bedrock_client import get_boto_session, CLAUDE_HAIKU_MODEL_ID


RESEARCH_AGENT_PROMPT = """You are a B2B company research specialist. Your job is to gather comprehensive, accurate information about companies for sales intelligence.

When researching a company, follow these steps IN ORDER:
1. If domain is unknown, call search_company_domain to find it
2. Call scrape_website on the company domain
3. Call enrich_with_apollo on the company domain — this returns a LinkedIn URL if available
4. If Apollo returned a LinkedIn URL, call scrape_linkedin with that URL to get deeper profile data (employees, tagline, about, size, headquarters, founded year)
5. Call compile_company_profile with ALL gathered information combined

IMPORTANT RULES:
- Always call compile_company_profile at the end — this is mandatory
- If a tool fails, continue with the remaining steps and compile whatever data you have
- Do NOT repeat tool calls unnecessarily
- Prefer LinkedIn data over Apollo for: description (use "about"), company_size, headquarters, founded_year
- Prefer Apollo for: industry classification
- Set confidence: 0.85+ if LinkedIn + Apollo both succeeded, 0.65 if only one source, 0.4 if neither

Execute the research systematically and compile the final profile."""


@tool
def search_company_domain(company_name: str) -> dict[str, Any]:
    """
    Search for a company's domain using Apollo.io search.
    
    Args:
        company_name: The name of the company to find the domain for.
        
    Returns:
        Dictionary with domain if found, or error message.
    """
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "content": [{"text": "Apollo API key not configured"}],
        }

    url = "https://api.apollo.io/api/v1/mixed_companies/search"
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

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        organizations = data.get("organizations", [])
        if organizations:
            name_lower = company_name.lower()
            for org in organizations:
                org_name = (org.get("name") or "").lower()
                if org_name == name_lower or name_lower in org_name:
                    domain = org.get("primary_domain")
                    if domain:
                        return {
                            "status": "success",
                            "content": [{"text": f"Found domain for {company_name}: {domain}"}],
                            "domain": domain,
                        }
            
            domain = organizations[0].get("primary_domain")
            if domain:
                return {
                    "status": "success",
                    "content": [{"text": f"Found domain for {company_name}: {domain}"}],
                    "domain": domain,
                }

        return {
            "status": "not_found",
            "content": [{"text": f"Could not find domain for {company_name}"}],
        }

    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Error searching for domain: {str(e)}"}],
        }


@tool
def scrape_website(url: str) -> dict[str, Any]:
    """
    Scrape a company website to extract business information.
    
    Args:
        url: The URL or domain to scrape (e.g., 'stripe.com' or 'https://stripe.com').
        
    Returns:
        Dictionary with scraped content including title, description, about text.
    """
    from bs4 import BeautifulSoup
    
    if not url:
        return {"status": "error", "content": [{"text": "No URL provided"}]}

    if not url.startswith("http"):
        url = f"https://{url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, verify=False) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")

        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        meta_description = None
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_description = meta_tag.get("content", "").strip()
        if not meta_description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc:
                meta_description = og_desc.get("content", "").strip()

        about_text = None
        for selector in [{"id": "about"}, {"class_": "about"}]:
            element = soup.find(["section", "div"], **selector)
            if element:
                text = element.get_text(separator=" ", strip=True)
                if len(text) > 50:
                    about_text = text[:500]
                    break

        industry_hints = []
        combined = (title or "") + " " + (meta_description or "")
        industry_keywords = {
            "fintech": ["fintech", "financial", "payments", "banking"],
            "saas": ["saas", "software", "platform", "cloud"],
            "ecommerce": ["ecommerce", "shopping", "retail"],
            "healthcare": ["healthcare", "health", "medical"],
            "ai_ml": ["artificial intelligence", "machine learning", "ai"],
        }
        for industry, keywords in industry_keywords.items():
            if any(kw in combined.lower() for kw in keywords):
                industry_hints.append(industry)

        content_parts = []
        if title:
            content_parts.append(f"Title: {title}")
        if meta_description:
            content_parts.append(f"Description: {meta_description}")
        if about_text:
            content_parts.append(f"About: {about_text}")
        if industry_hints:
            content_parts.append(f"Industry hints: {', '.join(industry_hints)}")

        return {
            "status": "success",
            "content": [{"text": "\n".join(content_parts) if content_parts else "No content extracted"}],
            "scraped_data": {
                "url": url,
                "title": title,
                "meta_description": meta_description,
                "about_text": about_text,
                "industry_hints": industry_hints,
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Failed to scrape {url}: {str(e)}"}],
        }


@tool
def enrich_with_apollo(domain: str) -> dict[str, Any]:
    """
    Enrich company data using Apollo.io API.
    
    Args:
        domain: The company domain to enrich (e.g., 'stripe.com').
        
    Returns:
        Dictionary with enriched company data including industry, size, HQ, description.
    """
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        return {"status": "error", "content": [{"text": "Apollo API key not configured"}]}

    if not domain:
        return {"status": "error", "content": [{"text": "No domain provided"}]}

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    url = "https://api.apollo.io/api/v1/organizations/enrich"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }
    params = {"domain": domain}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        org = data.get("organization", {})
        if not org:
            return {
                "status": "error",
                "content": [{"text": "No organization data returned from Apollo"}],
            }

        hq_parts = []
        if org.get("city"):
            hq_parts.append(org["city"])
        if org.get("state"):
            hq_parts.append(org["state"])
        if org.get("country"):
            hq_parts.append(org["country"])
        headquarters = ", ".join(hq_parts) if hq_parts else None

        employee_range = None
        count = org.get("estimated_num_employees")
        if count:
            if count < 10:
                employee_range = "1-10"
            elif count < 50:
                employee_range = "11-50"
            elif count < 200:
                employee_range = "51-200"
            elif count < 500:
                employee_range = "201-500"
            elif count < 1000:
                employee_range = "501-1000"
            elif count < 5000:
                employee_range = "1001-5000"
            else:
                employee_range = "5000+"

        content_parts = []
        if org.get("name"):
            content_parts.append(f"Company: {org['name']}")
        if org.get("industry"):
            content_parts.append(f"Industry: {org['industry']}")
        if employee_range:
            content_parts.append(f"Size: {employee_range} employees")
        if headquarters:
            content_parts.append(f"HQ: {headquarters}")
        if org.get("founded_year"):
            content_parts.append(f"Founded: {org['founded_year']}")
        if org.get("short_description"):
            content_parts.append(f"Description: {org['short_description']}")

        return {
            "status": "success",
            "content": [{"text": "\n".join(content_parts)}],
            "apollo_data": {
                "name": org.get("name"),
                "domain": org.get("primary_domain") or domain,
                "industry": org.get("industry"),
                "employee_range": employee_range,
                "headquarters": headquarters,
                "founded_year": org.get("founded_year"),
                "description": org.get("short_description") or org.get("seo_description"),
                "linkedin_url": org.get("linkedin_url"),
                "website_url": org.get("website_url"),
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Apollo enrichment failed: {str(e)}"}],
        }


@tool
def scrape_linkedin(linkedin_url: str) -> dict[str, Any]:
    """
    Scrape a LinkedIn company page using the Apify Actor to get deep profile data.
    Call this after enrich_with_apollo if a LinkedIn URL was returned.

    Args:
        linkedin_url: Slug-based LinkedIn company URL,
                      e.g. 'https://www.linkedin.com/company/stripe'.

    Returns:
        Dictionary with company details: about, tagline, size, headquarters,
        founded year, employees list, and more.
    """
    import asyncio
    from clients.apify_linkedin_client import scrape_linkedin_company

    if not linkedin_url:
        return {"status": "error", "content": [{"text": "No LinkedIn URL provided"}]}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, scrape_linkedin_company(linkedin_url))
                profile = future.result(timeout=120)
        else:
            profile = loop.run_until_complete(scrape_linkedin_company(linkedin_url))
    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"LinkedIn scrape failed: {str(e)}"}],
        }

    if not profile.success:
        return {
            "status": "error",
            "content": [{"text": profile.error or "LinkedIn scrape returned no data"}],
        }

    content_parts = []
    if profile.company_name:
        content_parts.append(f"Company: {profile.company_name}")
    if profile.tagline:
        content_parts.append(f"Tagline: {profile.tagline}")
    if profile.about:
        content_parts.append(f"About: {profile.about[:400]}")
    if profile.industry:
        content_parts.append(f"Industry: {profile.industry}")
    if profile.company_size:
        content_parts.append(f"Size: {profile.company_size}")
    if profile.headquarters:
        content_parts.append(f"HQ: {profile.headquarters}")
    if profile.founded:
        content_parts.append(f"Founded: {profile.founded}")
    if profile.company_type:
        content_parts.append(f"Type: {profile.company_type}")
    if profile.follower_count:
        content_parts.append(f"LinkedIn followers: {profile.follower_count}")
    if profile.employees:
        names = [e.get("name", "") for e in profile.employees[:3] if e.get("name")]
        if names:
            content_parts.append(f"Key employees: {', '.join(names)}")

    return {
        "status": "success",
        "content": [{"text": "\n".join(content_parts)}],
        "linkedin_data": {
            "company_name": profile.company_name,
            "tagline": profile.tagline,
            "about": profile.about,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "headquarters": profile.headquarters,
            "founded": profile.founded,
            "company_type": profile.company_type,
            "website": profile.website,
            "follower_count": profile.follower_count,
            "employees": profile.employees,
            "locations": profile.locations,
        },
    }


@tool
def compile_company_profile(
    name: str,
    domain: str = "",
    industry: str = "",
    headquarters: str = "",
    company_size: str = "",
    founded_year: str = "",
    description: str = "",
    linkedin_url: str = "",
    source_urls: str = "",
    confidence: float = 0.5,
) -> dict[str, Any]:
    """
    Compile all gathered information into a final company profile.
    ALWAYS call this tool at the end of research with all gathered data.
    
    Args:
        name: Official company name (required).
        domain: Primary website domain.
        industry: Industry classification.
        headquarters: HQ location (city, state/region, country).
        company_size: Employee count range (e.g., '51-200').
        founded_year: Year the company was founded.
        description: Brief business description (1-2 sentences).
        linkedin_url: LinkedIn company page URL.
        source_urls: Comma-separated list of URLs used as sources.
        confidence: Overall confidence in the profile (0.0 to 1.0).
    """
    sources = [s.strip() for s in source_urls.split(",") if s.strip()]
    
    profile_data = {
        "name": name or "Unknown Company",
        "domain": domain or None,
        "industry": industry or None,
        "headquarters": headquarters or None,
        "company_size": company_size or None,
        "founded_year": founded_year or None,
        "description": description or None,
        "linkedin_url": linkedin_url or None,
        "source_links": sources,
        "confidence": max(0.0, min(1.0, confidence)),
    }
    
    return {
        "status": "success",
        "content": [{"text": f"Compiled profile for {name} with {confidence:.0%} confidence"}],
        "profile": profile_data,
    }


class ProfileCaptureHook(HookProvider):
    """
    Captures the result of compile_company_profile via Strands hook system.
    This is the reliable way to extract structured data from a tool call
    without parsing the agent's text output.

    AfterToolCallEvent fields:
      - tool_use.name: name of the tool called
      - result: ToolResult dict with "content" list
    """

    def __init__(self) -> None:
        self.captured_profile: Optional[dict] = None

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AfterToolCallEvent, self._on_after_tool)

    def _on_after_tool(self, event: AfterToolCallEvent) -> None:
        if event.tool_use.get("name") != "compile_company_profile":
            return
        if event.exception:
            return
        result = event.result
        # Strands passes the tool's return dict through as-is (adding toolUseId).
        # Our compile_company_profile returns {"status": "success", "content": [...], "profile": {...}}
        # so the extra "profile" key is preserved directly on the result dict.
        if isinstance(result, dict) and result.get("status") == "success":
            self.captured_profile = result.get("profile")


def _build_agent(hook: ProfileCaptureHook) -> Agent:
    """Create a fresh agent instance with the given hook."""
    boto_session = get_boto_session()
    model = BedrockModel(
        model_id=CLAUDE_HAIKU_MODEL_ID,
        boto_session=boto_session,
        temperature=0.2,
        max_tokens=4096,
    )
    return Agent(
        model=model,
        system_prompt=RESEARCH_AGENT_PROMPT,
        tools=[
                search_company_domain,
                scrape_website,
                enrich_with_apollo,
                scrape_linkedin,
                compile_company_profile,
            ],
        hooks=[hook],
    )


async def research_company(candidate: CompanyCandidate) -> CompanyProfile:
    """
    Research a company using the Strands Agent.

    A fresh agent + hook is created per request so that concurrent requests
    don't share state. The hook captures the compile_company_profile result
    directly from the tool call event, bypassing any need to parse text.
    """
    hook = ProfileCaptureHook()
    agent = _build_agent(hook)

    query_parts = []
    if candidate.name:
        query_parts.append(f"Company name: {candidate.name}")
    if candidate.domain:
        query_parts.append(f"Known domain: {candidate.domain}")

    query = f"""Research this company and compile a complete profile:

{chr(10).join(query_parts)}

Execute these steps:
1. {"Use the known domain: " + candidate.domain if candidate.domain else "Find the company domain using search_company_domain"}
2. Scrape the website using scrape_website
3. Enrich with Apollo using enrich_with_apollo
4. Call compile_company_profile with ALL gathered information

Start now."""

    try:
        await agent.invoke_async(query)

        if hook.captured_profile:
            return CompanyProfile(**hook.captured_profile)

        return await _fallback_research(candidate)

    except Exception as e:
        print(f"Strands agent failed: {e}")
        return await _fallback_research(candidate)


async def _fallback_research(candidate: CompanyCandidate) -> CompanyProfile:
    """Fallback to direct API calls if agent fails."""
    from clients.apollo_client import enrich_organization, search_organization_by_name
    from clients.scraper import scrape_company_website
    
    domain = candidate.domain
    company_name = candidate.name
    source_links = []
    
    if not domain and company_name:
        domain = await search_organization_by_name(company_name)
        if domain:
            source_links.append(f"https://{domain}")

    scraped = None
    if domain:
        scraped = await scrape_company_website(domain)
        if scraped.success:
            source_links.append(scraped.url)

    apollo = None
    if domain:
        apollo = await enrich_organization(domain)
        if apollo.success and apollo.linkedin_url:
            source_links.append(apollo.linkedin_url)

    name = apollo.name if apollo and apollo.success else candidate.name
    industry = apollo.industry if apollo and apollo.success else None
    if not industry and scraped and scraped.success and scraped.industry_hints:
        industry = scraped.industry_hints[0].replace("_", " ").title()

    description = None
    if apollo and apollo.success and apollo.description:
        description = apollo.description
    elif scraped and scraped.success:
        description = scraped.meta_description or scraped.about_text

    confidence = 0.0
    if name:
        confidence += 0.2
    if domain:
        confidence += 0.2
    if industry:
        confidence += 0.15
    if description:
        confidence += 0.15
    if apollo and apollo.success:
        confidence += 0.2
    if scraped and scraped.success:
        confidence += 0.1

    return CompanyProfile(
        name=name or "Unknown Company",
        domain=domain,
        industry=industry,
        headquarters=apollo.headquarters if apollo and apollo.success else None,
        company_size=apollo.employee_range if apollo and apollo.success else None,
        founded_year=str(apollo.founded_year) if apollo and apollo.success and apollo.founded_year else None,
        description=description,
        linkedin_url=apollo.linkedin_url if apollo and apollo.success else None,
        source_links=source_links,
        confidence=min(1.0, confidence),
    )

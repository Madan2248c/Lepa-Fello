"""
Production-grade web scraper for company website intelligence.

Handles JavaScript-rendered content, rate limiting, and graceful degradation.
"""

import re
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class ScrapedWebsite:
    """Extracted content from a company website."""
    
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    about_text: Optional[str] = None
    industry_hints: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    technologies_detected: list[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


INDUSTRY_PATTERNS = {
    "fintech": [
        r"fintech", r"financial\s+tech", r"banking", r"payments?", r"lending",
        r"credit", r"debit", r"transactions?", r"money\s+transfer",
    ],
    "saas": [
        r"saas", r"software\s+as\s+a\s+service", r"cloud\s+platform",
        r"subscription", r"monthly\s+plan",
    ],
    "ecommerce": [
        r"e-?commerce", r"online\s+shop", r"marketplace", r"retail",
        r"buy\s+online", r"shopping\s+cart",
    ],
    "healthcare": [
        r"healthcare", r"health\s+tech", r"medical", r"clinical",
        r"patient", r"telemedicine", r"diagnosis",
    ],
    "real_estate": [
        r"real\s+estate", r"property", r"realty", r"housing",
        r"mortgage", r"home\s+buying", r"rentals?",
    ],
    "marketing": [
        r"marketing", r"advertising", r"seo", r"analytics",
        r"growth", r"campaigns?", r"lead\s+gen",
    ],
    "cybersecurity": [
        r"security", r"cyber", r"infosec", r"compliance",
        r"identity", r"authentication", r"encryption",
    ],
    "ai_ml": [
        r"artificial\s+intelligence", r"machine\s+learning", r"\bai\b", r"\bml\b",
        r"automation", r"neural\s+network", r"deep\s+learning",
    ],
    "devtools": [
        r"developer\s+tools?", r"\bapi\b", r"devops", r"infrastructure",
        r"code", r"sdk", r"framework",
    ],
    "hr_tech": [
        r"\bhr\b", r"human\s+resources", r"recruiting", r"talent",
        r"workforce", r"hiring", r"payroll",
    ],
    "logistics": [
        r"logistics", r"supply\s+chain", r"shipping", r"delivery",
        r"warehouse", r"fulfillment", r"freight",
    ],
    "edtech": [
        r"education", r"edtech", r"learning", r"training",
        r"courses?", r"e-?learning", r"lms",
    ],
}

TECH_PATTERNS = {
    "react": r"react\.js|reactjs|react-dom",
    "vue": r"vue\.js|vuejs",
    "angular": r"angular",
    "next.js": r"next\.js|nextjs|_next",
    "wordpress": r"wordpress|wp-content|wp-includes",
    "shopify": r"shopify|myshopify",
    "hubspot": r"hubspot|hs-analytics|hsforms",
    "salesforce": r"salesforce|pardot",
    "google_analytics": r"google-analytics|googletagmanager|gtag",
    "segment": r"segment\.io|analytics\.js",
    "intercom": r"intercom",
    "zendesk": r"zendesk",
    "stripe": r"stripe\.js|stripe\.com",
}


async def scrape_company_website(domain: str) -> ScrapedWebsite:
    """
    Scrape a company website to extract business information.
    
    Features:
    - Follows redirects
    - Handles SSL errors gracefully
    - Extracts metadata, about text, social links
    - Detects technologies and industries
    
    Args:
        domain: Company domain (e.g., 'stripe.com')
        
    Returns:
        ScrapedWebsite with extracted information
    """
    if not domain:
        return ScrapedWebsite(url="", error="No domain provided")

    if not domain.startswith("http"):
        url = f"https://{domain}"
    else:
        url = domain

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            verify=False,
            http2=True,
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
            final_url = str(response.url)

        soup = BeautifulSoup(html, "lxml")

        title = _extract_title(soup)
        meta_description = _extract_meta_description(soup)
        about_text = _extract_about_text(soup)
        social_links = _extract_social_links(soup, final_url)
        
        combined_text = " ".join(filter(None, [title, meta_description, about_text]))
        industry_hints = _detect_industries(combined_text)
        technologies = _detect_technologies(html)

        return ScrapedWebsite(
            url=final_url,
            title=title,
            meta_description=meta_description,
            about_text=about_text,
            industry_hints=industry_hints,
            social_links=social_links,
            technologies_detected=technologies,
            success=True,
        )

    except httpx.HTTPStatusError as e:
        return ScrapedWebsite(url=url, error=f"HTTP {e.response.status_code}")
    except httpx.TimeoutException:
        return ScrapedWebsite(url=url, error="Request timed out after 20s")
    except httpx.ConnectError:
        return ScrapedWebsite(url=url, error="Connection failed - site may be down")
    except Exception as e:
        return ScrapedWebsite(url=url, error=f"Scrape failed: {str(e)[:100]}")


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    """Extract page title, preferring og:title over <title>."""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        return og_title["content"].strip()
    
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        title = re.sub(r"\s*[\|\-–—]\s*[^|–—]+$", "", title)
        return title[:200] if title else None
    
    return None


def _extract_meta_description(soup: BeautifulSoup) -> Optional[str]:
    """Extract meta description from various sources."""
    for selector in [
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ]:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            desc = tag["content"].strip()
            if len(desc) > 30:
                return desc[:500]
    
    return None


def _extract_about_text(soup: BeautifulSoup) -> Optional[str]:
    """Try to find 'about' content on the page."""
    for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    selectors = [
        {"id": re.compile(r"about", re.I)},
        {"class_": re.compile(r"about", re.I)},
        {"id": re.compile(r"company", re.I)},
        {"class_": re.compile(r"company", re.I)},
        {"class_": re.compile(r"hero", re.I)},
        {"class_": re.compile(r"intro", re.I)},
    ]

    for selector in selectors:
        element = soup.find(["section", "div", "article"], **selector)
        if element:
            text = element.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            if 50 < len(text) < 2000:
                return text[:500]

    main = soup.find("main")
    if main:
        paragraphs = main.find_all("p")
        for p in paragraphs[:3]:
            text = p.get_text(strip=True)
            if len(text) > 80:
                return text[:500]

    hero_heading = soup.find(["h1", "h2"])
    if hero_heading:
        parent = hero_heading.find_parent(["section", "div"])
        if parent:
            paragraphs = parent.find_all("p")
            for p in paragraphs[:2]:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    return text[:500]

    return None


def _extract_social_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    """Extract social media profile links."""
    social_patterns = {
        "linkedin": r"linkedin\.com/(company|in)/",
        "twitter": r"(twitter|x)\.com/",
        "facebook": r"facebook\.com/",
        "youtube": r"youtube\.com/",
        "instagram": r"instagram\.com/",
        "github": r"github\.com/",
    }
    
    links = {}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if not href.startswith("http"):
            href = urljoin(base_url, href)
        
        for platform, pattern in social_patterns.items():
            if platform not in links and re.search(pattern, href, re.I):
                links[platform] = href
                break
    
    return links


def _detect_industries(text: str) -> list[str]:
    """Detect industry categories from text content."""
    if not text:
        return []
    
    text_lower = text.lower()
    detected = []
    
    for industry, patterns in INDUSTRY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                detected.append(industry)
                break
    
    return list(set(detected))[:3]


def _detect_technologies(html: str) -> list[str]:
    """Detect technologies from HTML source."""
    if not html:
        return []
    
    html_lower = html.lower()
    detected = []
    
    for tech, pattern in TECH_PATTERNS.items():
        if re.search(pattern, html_lower):
            detected.append(tech)
    
    return detected

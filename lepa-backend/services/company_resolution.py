from typing import Optional

from schemas.internal_models import (
    NormalizedAccountInput,
    CompanyCandidate,
    IPInfoResult,
)
from clients.ipinfo_client import lookup_ip, is_likely_business_ip


async def resolve_company_from_visitor(
    normalized_input: NormalizedAccountInput,
) -> CompanyCandidate:
    """
    Attempt to identify a company from visitor signals.
    
    Primary method: IP address lookup via IPInfo Lite.
    Returns a CompanyCandidate with confidence based on signal quality.
    """
    visitor_ctx = normalized_input.visitor_context
    ip_address = visitor_ctx.ip_address

    if not ip_address:
        return CompanyCandidate(
            name=None,
            domain=None,
            source="ip_lookup",
            confidence=0.0,
            confidence_reasons=["No IP address provided"],
            raw_ip_info=None,
        )

    ip_info = await lookup_ip(ip_address)

    if not ip_info:
        return CompanyCandidate(
            name=None,
            domain=None,
            source="ip_lookup",
            confidence=0.0,
            confidence_reasons=["IPInfo lookup failed or no token configured"],
            raw_ip_info=None,
        )

    is_business, reasons = is_likely_business_ip(ip_info)

    if is_business and ip_info.as_domain:
        confidence = 0.7
        name = ip_info.as_name
        domain = ip_info.as_domain
    elif ip_info.as_name:
        confidence = 0.3
        name = ip_info.as_name
        domain = ip_info.as_domain
        reasons.append("Low confidence: may be ISP or hosting, not direct company")
    else:
        confidence = 0.1
        name = None
        domain = None
        reasons.append("Minimal organization data available")

    return CompanyCandidate(
        name=name,
        domain=domain,
        source="ip_lookup",
        confidence=confidence,
        confidence_reasons=reasons,
        raw_ip_info=ip_info,
    )


def resolve_company_from_seed(
    normalized_input: NormalizedAccountInput,
) -> CompanyCandidate:
    """
    Create a company candidate from direct company seed input.
    
    The seed input is trusted as the starting point, but will be
    enriched by the research agent.
    """
    seed = normalized_input.company_seed

    if not seed.name:
        return CompanyCandidate(
            name=None,
            domain=None,
            source="company_seed",
            confidence=0.0,
            confidence_reasons=["No company name provided"],
            raw_ip_info=None,
        )

    reasons = [f"Company name provided directly: {seed.name}"]
    confidence = 0.9

    domain = seed.partial_domain
    if domain:
        if not domain.startswith("http") and "." not in domain:
            domain = f"{domain}.com"
        reasons.append(f"Domain hint provided: {domain}")
    else:
        confidence = 0.8
        reasons.append("No domain hint; will attempt to resolve via research")

    return CompanyCandidate(
        name=seed.name,
        domain=domain,
        source="company_seed",
        confidence=confidence,
        confidence_reasons=reasons,
        raw_ip_info=None,
    )

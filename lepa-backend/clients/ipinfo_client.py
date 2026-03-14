import os
import asyncio
from typing import Optional

import ipinfo

from schemas.internal_models import IPInfoResult


def _get_handler() -> ipinfo.handler_lite.HandlerLite:
    token = os.getenv("IPINFO_TOKEN")
    if not token:
        raise ValueError("IPINFO_TOKEN not configured")
    return ipinfo.getHandlerLite(access_token=token)


async def lookup_ip(ip_address: str) -> Optional[IPInfoResult]:
    """
    Look up an IP address using the IPInfo Lite SDK.

    The SDK is synchronous so we run it in a thread pool to avoid
    blocking FastAPI's async event loop.

    IPInfo Lite returns: ip, asn, as_name, as_domain,
                         country_code, country, continent_code, continent
    """
    try:
        handler = _get_handler()
    except ValueError:
        return None

    def _fetch() -> dict:
        details = handler.getDetails(ip_address)
        return details.all

    try:
        data = await asyncio.to_thread(_fetch)

        # The SDK returns continent and country as dicts: {'code': 'AS', 'name': 'Asia'}
        # Extract the string values before passing to the Pydantic model.
        continent_raw = data.get("continent")
        country_raw = data.get("country")

        return IPInfoResult(
            ip=data.get("ip", ip_address),
            asn=data.get("asn"),
            as_name=data.get("as_name"),
            as_domain=data.get("as_domain"),
            country_code=data.get("country_code"),
            country=country_raw.get("name") if isinstance(country_raw, dict) else country_raw,
            continent_code=continent_raw.get("code") if isinstance(continent_raw, dict) else data.get("continent_code"),
            continent=continent_raw.get("name") if isinstance(continent_raw, dict) else continent_raw,
        )

    except Exception as e:
        print(f"IPInfo lookup failed for {ip_address}: {e}")
        return None


def is_likely_business_ip(ip_info: IPInfoResult) -> tuple[bool, list[str]]:
    """
    Determine if an IP likely belongs to a business vs consumer/hosting.

    Returns (is_business, reasons).
    """
    reasons = []

    if not ip_info.as_domain:
        reasons.append("No AS domain available")
        return False, reasons

    hosting_indicators = [
        "amazon", "aws", "google", "cloud", "azure", "digitalocean",
        "linode", "vultr", "hetzner", "ovh", "hostinger", "godaddy",
        "cloudflare", "akamai", "fastly", "vpn", "proxy", "tor",
    ]

    isp_indicators = [
        "telecom", "telekom", "broadband", "cable", "wireless", "mobile",
        "verizon", "comcast", "att", "t-mobile", "sprint", "vodafone",
        "orange", "telefonica", "bt.com", "sky.com", "charter", "cox",
    ]

    as_domain_lower = ip_info.as_domain.lower()
    as_name_lower = (ip_info.as_name or "").lower()

    for indicator in hosting_indicators:
        if indicator in as_domain_lower or indicator in as_name_lower:
            reasons.append(f"Hosting/cloud provider detected: {ip_info.as_name}")
            return False, reasons

    for indicator in isp_indicators:
        if indicator in as_domain_lower or indicator in as_name_lower:
            reasons.append(f"Consumer ISP detected: {ip_info.as_name}")
            return False, reasons

    reasons.append(f"Business AS domain detected: {ip_info.as_domain}")
    if ip_info.as_name:
        reasons.append(f"Organization: {ip_info.as_name}")

    return True, reasons

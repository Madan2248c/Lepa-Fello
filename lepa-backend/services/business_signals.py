"""
Business signal discovery service.

Uses Exa neural search to find recent public signals about a company:
- Funding rounds
- Hiring activity / job postings
- Market expansion
- Product launches
- Leadership changes

Each signal is classified, deduplicated, and returned with source URL,
date, and confidence.
"""

import re
from typing import Optional

from schemas.output_models import BusinessSignal
from clients.exa_client import search_business_signals, ExaResult


SIGNAL_PATTERNS: dict[str, list[str]] = {
    "funding": [
        r"raises?\s+\$[\d\.]+[mb]",
        r"series\s+[a-e]\b",
        r"seed\s+round",
        r"funding\s+round",
        r"venture\s+capital",
        r"investment\s+of",
        r"valued\s+at",
        r"valuation",
        r"ipo",
        r"spac",
        r"acqui",
    ],
    "hiring": [
        r"hiring",
        r"we['']re\s+hiring",
        r"join\s+our\s+team",
        r"open\s+positions?",
        r"job\s+openings?",
        r"expanding\s+(its\s+)?team",
        r"headcount",
        r"new\s+hires?",
        r"talent\s+acquisition",
    ],
    "expansion": [
        r"expands?\s+(to|into)",
        r"launches?\s+in",
        r"new\s+market",
        r"international\s+expansion",
        r"opens?\s+(new\s+)?office",
        r"new\s+region",
        r"global\s+expansion",
        r"enters?\s+(the\s+)?\w+\s+market",
    ],
    "product_launch": [
        r"launches?\s+(new|its)",
        r"announces?\s+(new|its)",
        r"introduces?\s+",
        r"unveils?\s+",
        r"releases?\s+(new|version|v\d)",
        r"new\s+product",
        r"new\s+feature",
        r"general\s+availability",
        r"\bga\b",
    ],
}

SIGNAL_CONFIDENCE_BASE = 0.75


async def discover_business_signals(
    company_name: str,
    domain: Optional[str] = None,
    max_signals: int = 5,
) -> tuple[list[BusinessSignal], list[str]]:
    """
    Discover public business signals for a company using Exa.

    Args:
        company_name: Name of the company.
        domain: Optional domain to improve search targeting.
        max_signals: Maximum number of signals to return.

    Returns:
        Tuple of (signals list, news source URLs list).
    """
    exa_response = await search_business_signals(
        company_name=company_name,
        domain=domain,
        num_results=10,
    )

    if not exa_response.success or not exa_response.results:
        return [], []

    signals: list[BusinessSignal] = []
    news_links: list[str] = []
    seen_urls: set[str] = set()

    for result in exa_response.results:
        if result.url in seen_urls:
            continue
        seen_urls.add(result.url)

        if result.url:
            news_links.append(result.url)

        signal_type, confidence = _classify_signal(result)
        if signal_type is None:
            continue

        summary = _build_summary(result, signal_type)
        if not summary:
            continue

        signals.append(
            BusinessSignal(
                type=signal_type,  # type: ignore[arg-type]
                summary=summary,
                published_at=_normalize_date(result.published_date),
                source_url=result.url or None,
                confidence=confidence,
            )
        )

        if len(signals) >= max_signals:
            break

    signals = _deduplicate_signals(signals)
    return signals[:max_signals], news_links


def _classify_signal(
    result: ExaResult,
) -> tuple[Optional[str], float]:
    """
    Classify an Exa result into a signal type.

    Checks title + first 500 chars of text against SIGNAL_PATTERNS.
    Returns (signal_type, confidence) or (None, 0) if no match.
    """
    text_to_check = " ".join(
        filter(None, [result.title, (result.text or "")[:500]])
    ).lower()

    for signal_type, patterns in SIGNAL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_to_check, re.I):
                confidence = SIGNAL_CONFIDENCE_BASE
                if result.score and result.score > 0.8:
                    confidence = min(0.95, confidence + 0.1)
                return signal_type, round(confidence, 2)

    return None, 0.0


def _build_summary(result: ExaResult, signal_type: str) -> str:
    """
    Build a concise signal summary from the result title and text.

    Prefers the article title. Falls back to the first sentence of text.
    """
    if result.title and len(result.title) > 20:
        return result.title[:200]

    if result.text:
        first_sentence = re.split(r"(?<=[.!?])\s+", result.text.strip())[0]
        if len(first_sentence) > 30:
            return first_sentence[:200]

    return f"{signal_type.replace('_', ' ').title()} signal detected"


def _normalize_date(raw_date: Optional[str]) -> Optional[str]:
    """Normalize Exa's published date to ISO-8601 date string (YYYY-MM-DD)."""
    if not raw_date:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", raw_date)
    return match.group(0) if match else None


def _deduplicate_signals(signals: list[BusinessSignal]) -> list[BusinessSignal]:
    """
    Remove near-duplicate signals of the same type.

    Keeps the highest-confidence signal per type, unless multiple
    distinct events of the same type exist (e.g., two funding rounds).
    """
    type_counts: dict[str, int] = {}
    result: list[BusinessSignal] = []

    for signal in sorted(signals, key=lambda s: s.confidence, reverse=True):
        count = type_counts.get(signal.type, 0)
        if count < 2:
            result.append(signal)
            type_counts[signal.type] = count + 1

    return result

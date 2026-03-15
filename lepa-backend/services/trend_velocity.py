"""
Trend velocity / signal surge detection service.

Detects whether a company's public activity is SURGING, STABLE, or DECLINING
by comparing recent signal density against a baseline window.

Uses Exa to fetch recent news/signals and measures publication frequency.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from clients.exa_client import search_business_signals_dated

logger = logging.getLogger("lepa.trend_velocity")


async def detect_trend_velocity(
    company_name: str,
    domain: Optional[str] = None,
) -> dict:
    """
    Detect signal velocity for a company.

    Compares:
    - Recent window: last 30 days
    - Baseline window: 31-90 days ago

    Returns a velocity dict with:
    - status: "surging" | "stable" | "declining" | "unknown"
    - recent_signal_count: int
    - baseline_signal_count: int
    - velocity_ratio: float (recent/baseline, normalized to 30-day periods)
    - surge_topics: list[str] — what topics are spiking
    - interpretation: str — human-readable explanation
    """
    if not company_name:
        return _unknown_velocity()

    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=30)
    baseline_start = now - timedelta(days=90)
    baseline_end = now - timedelta(days=31)

    try:
        # Fetch recent signals (last 30 days)
        recent_response = await search_business_signals_dated(
            company_name=company_name,
            domain=domain,
            num_results=10,
            start_published_date=recent_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        # Fetch baseline signals (31-90 days ago)
        baseline_response = await search_business_signals_dated(
            company_name=company_name,
            domain=domain,
            num_results=10,
            start_published_date=baseline_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_published_date=baseline_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
    except Exception as e:
        logger.warning(f"Trend velocity search failed for {company_name}: {e}")
        return _unknown_velocity()

    recent_count = len(recent_response.results) if recent_response.success else 0
    # Baseline covers 60 days, normalize to 30-day equivalent
    baseline_count_raw = len(baseline_response.results) if baseline_response.success else 0
    baseline_count_normalized = baseline_count_raw / 2.0

    if baseline_count_normalized == 0:
        if recent_count > 0:
            ratio = 3.0  # treat as surging if no baseline but recent activity
        else:
            return _unknown_velocity()
    else:
        ratio = recent_count / baseline_count_normalized

    # Extract surge topics from recent results
    surge_topics = _extract_topics(recent_response.results if recent_response.success else [])

    if ratio >= 2.0:
        status = "surging"
        interpretation = (
            f"{company_name} has {recent_count} signals in the last 30 days vs "
            f"~{baseline_count_raw} in the prior 60 days — activity is surging ({ratio:.1f}x baseline)."
        )
    elif ratio >= 0.7:
        status = "stable"
        interpretation = (
            f"{company_name} shows consistent activity ({recent_count} recent signals, "
            f"ratio {ratio:.1f}x baseline)."
        )
    else:
        status = "declining"
        interpretation = (
            f"{company_name} activity appears to be declining ({recent_count} recent signals "
            f"vs ~{baseline_count_raw} in prior period)."
        )

    return {
        "status": status,
        "recent_signal_count": recent_count,
        "baseline_signal_count": baseline_count_raw,
        "velocity_ratio": round(ratio, 2),
        "surge_topics": surge_topics[:5],
        "interpretation": interpretation,
    }


def _extract_topics(results: list) -> list[str]:
    """Extract key topic words from result titles/summaries."""
    topic_keywords = [
        "funding", "raised", "series", "acquisition", "acquired", "merger",
        "hiring", "expansion", "launch", "partnership", "product", "growth",
        "ipo", "revenue", "customers", "enterprise", "ai", "platform",
    ]
    found = []
    for result in results:
        text = ((getattr(result, "title", "") or "") + " " + (getattr(result, "text", "") or "")).lower()
        for kw in topic_keywords:
            if kw in text and kw not in found:
                found.append(kw)
    return found


def _unknown_velocity() -> dict:
    return {
        "status": "unknown",
        "recent_signal_count": 0,
        "baseline_signal_count": 0,
        "velocity_ratio": 0.0,
        "surge_topics": [],
        "interpretation": "Insufficient data to determine signal velocity.",
    }

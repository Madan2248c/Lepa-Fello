"""
Simple result caching - store analysis results and retrieve them.
"""

import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# In-memory cache for simplicity
_cache: Dict[str, Dict[str, Any]] = {}

def _generate_cache_key(tenant_id: str, input_type: str, input_data: Dict[str, Any]) -> str:
    """Generate a stable cache key from input data."""
    # Create a stable hash from the input
    if input_type == "visitor":
        # For visitors, use IP + pages visited as key
        key_data = {
            "ip": input_data.get("ip_address", ""),
            "pages": sorted(input_data.get("pages_visited", [])),
            "type": "visitor"
        }
    else:  # company
        # For companies, use domain or company name
        key_data = {
            "domain": input_data.get("domain", "").lower(),
            "company": input_data.get("company_name", "").lower(),
            "type": "company"
        }
    
    cache_input = f"{tenant_id}:{json.dumps(key_data, sort_keys=True)}"
    return hashlib.md5(cache_input.encode()).hexdigest()

def store_result(tenant_id: str, input_type: str, input_data: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Store analysis result in cache (JSON-safe — datetimes serialized to strings)."""
    cache_key = _generate_cache_key(tenant_id, input_type, input_data)
    # Round-trip through JSON to convert datetimes/enums to primitives
    safe_result = json.loads(json.dumps(result, default=str))
    _cache[cache_key] = {
        "result": safe_result,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "input_type": input_type,
        "tenant_id": tenant_id
    }

def get_cached_result(tenant_id: str, input_type: str, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retrieve cached analysis result."""
    cache_key = _generate_cache_key(tenant_id, input_type, input_data)
    cached = _cache.get(cache_key)
    if cached:
        return cached["result"]
    return None

def list_cached_results(tenant_id: str, limit: int = 50) -> list[Dict[str, Any]]:
    """List all cached results for a tenant (in-memory only)."""
    results = []
    for cache_key, cached_data in _cache.items():
        if cached_data["tenant_id"] == tenant_id:
            result = cached_data["result"]
            results.append({
                "cache_key": cache_key,
                "company_name": result.get("company_profile", {}).get("name", "Unknown"),
                "domain": result.get("company_profile", {}).get("domain", ""),
                "cached_at": cached_data["cached_at"],
                "input_type": cached_data["input_type"],
            })
    results.sort(key=lambda x: x["cached_at"], reverse=True)
    return results[:limit]


def get_cache_stats(tenant_id: str) -> Dict[str, int]:
    results = list_cached_results(tenant_id, limit=1000)
    return {
        "total": len(results),
        "visitors": len([r for r in results if r["input_type"] == "visitor"]),
        "companies": len([r for r in results if r["input_type"] == "company"]),
    }

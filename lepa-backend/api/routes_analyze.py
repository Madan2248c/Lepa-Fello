"""
Analysis API routes for visitor and company intelligence.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from schemas.input_models import VisitorSignalInput, CompanySeedInput
from schemas.output_models import AnalyzeResponse
from services.result_cache import store_result, get_cached_result, list_cached_results, get_cache_stats

logger = logging.getLogger("lepa.api")

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post(
    "/visitor",
    response_model=AnalyzeResponse,
    summary="Analyze website visitor",
    description="""
Analyze a website visitor's behavior to generate account intelligence.

**Input**: Visitor signals including:
- Pages visited (e.g., /pricing, /docs, /case-studies)
- Time on site
- Number of visits this week
- IP address (for company identification)
- Referral source

**Output**: Complete account intelligence including:
- Company identification from IP
- Visitor persona inference
- Buying intent score
- AI-generated summary
- Recommended sales actions
    """,
)
async def analyze_visitor(
    input_data: VisitorSignalInput,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> AnalyzeResponse:
    """Analyze a website visitor to generate account intelligence."""
    from services.pipeline import run_visitor_pipeline
    from clients.db_client import get_cached_result as db_get_cached, get_visitor_account_id

    tenant_id = x_tenant_id or "default"

    # Check in-memory cache first (same server session)
    cached = get_cached_result(tenant_id, "visitor", input_data.model_dump())
    if cached:
        logger.info(f"Returning in-memory cached result for visitor: {input_data.visitor_id}")
        return JSONResponse(content=cached)

    # Look up the account_id previously resolved for this visitor (stored in DB)
    account_id = await get_visitor_account_id(tenant_id, input_data.visitor_id)
    if account_id:
        db_cached = await db_get_cached(tenant_id, account_id)
        if db_cached:
            logger.info(f"Returning DB cached result for visitor: {input_data.visitor_id} -> {account_id}")
            store_result(tenant_id, "visitor", input_data.model_dump(), db_cached)
            return JSONResponse(content=db_cached)

    start_time = time.time()
    logger.info(f"Starting visitor analysis: {input_data.visitor_id} (tenant={tenant_id})")

    try:
        result = await run_visitor_pipeline(input_data, tenant_id=tenant_id)

        # Store result in cache
        store_result(tenant_id, "visitor", input_data.model_dump(), result.model_dump())

        # Link visitor_id -> resolved account_id so future requests hit DB cache
        if result.domain or result.account_name:
            import re
            from clients.db_client import set_visitor_account_id
            resolved_id = re.sub(r"[^a-z0-9\.\-]", "", result.domain.lower()) if result.domain \
                else re.sub(r"[^a-z0-9]", "_", result.account_name.lower().strip())
            await set_visitor_account_id(tenant_id, input_data.visitor_id, resolved_id)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Visitor analysis complete: {input_data.visitor_id} "
            f"(account={result.account_name}, confidence={result.overall_confidence:.0%}, "
            f"elapsed={elapsed:.2f}s)"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error in visitor analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Visitor analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)[:200]}",
        )


@router.post(
    "/company",
    response_model=AnalyzeResponse,
    summary="Analyze company by name",
    description="""
Analyze a company by name to generate account intelligence.

**Input**: Company information including:
- Company name (required)
- Partial domain hint (optional)

**Output**: Complete account intelligence including:
- Enriched company profile (industry, size, HQ, etc.)
- Default persona (no visitor behavior available)
- Default intent score
- AI-generated summary
- Recommended sales actions

**Data Sources**:
- Apollo.io for company enrichment
- Company website scraping
- Strands AI agent for research synthesis
    """,
)
async def analyze_company(
    input_data: CompanySeedInput,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> AnalyzeResponse:
    """Analyze a company by name to generate account intelligence."""
    from services.pipeline import run_company_pipeline
    from clients.db_client import get_cached_result as db_get_cached
    import re

    tenant_id = x_tenant_id or "default"

    # Check in-memory cache first
    cached = get_cached_result(tenant_id, "company", input_data.model_dump())
    if cached:
        logger.info(f"Returning in-memory cached result for company: {input_data.company_name}")
        return JSONResponse(content=cached)

    # Derive account_id the same way history.py does: domain > normalized name
    if input_data.partial_domain:
        account_id = input_data.partial_domain.lower().replace("www.", "").strip("/")
        account_id = re.sub(r"[^a-z0-9\.\-]", "", account_id)
    else:
        account_id = re.sub(r"[^a-z0-9]", "_", input_data.company_name.lower().strip())

    db_cached = await db_get_cached(tenant_id, account_id)
    if db_cached:
        logger.info(f"Returning DB cached result for company: {input_data.company_name}")
        store_result(tenant_id, "company", input_data.model_dump(), db_cached)
        return JSONResponse(content=db_cached)

    start_time = time.time()
    logger.info(f"Starting company analysis: {input_data.company_name} (tenant={tenant_id})")

    try:
        result = await run_company_pipeline(input_data, tenant_id=tenant_id)
        
        # Store result in cache
        store_result(tenant_id, "company", input_data.model_dump(), result.model_dump())
        
        elapsed = time.time() - start_time
        logger.info(
            f"Company analysis complete: {input_data.company_name} "
            f"(domain={result.domain}, confidence={result.overall_confidence:.0%}, "
            f"elapsed={elapsed:.2f}s)"
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error in company analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Company analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)[:200]}",
        )


@router.get(
    "/results",
    summary="List cached analysis results",
    description="Returns all cached analysis results for the tenant.",
)
async def list_results(
    limit: int = Query(default=50, le=100),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    """List all cached analysis results for a tenant."""
    tenant_id = x_tenant_id or "default"
    results = list_cached_results(tenant_id, limit)
    return {"total": len(results), "results": results}


@router.get(
    "/stats",
    summary="Get analysis statistics",
    description="Returns statistics about cached analysis results.",
)
async def get_stats(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    """Get analysis statistics for a tenant."""
    tenant_id = x_tenant_id or "default"
    from clients.db_client import _connect
    import json as _json

    conn = await _connect()
    try:
        count_rows = await conn.fetch("""
            SELECT input_type, COUNT(*) as cnt
            FROM pipeline_runs WHERE tenant_id = $1
            GROUP BY input_type
        """, tenant_id)
        counts = {r["input_type"]: r["cnt"] for r in count_rows}

        recent_rows = await conn.fetch("""
            SELECT account_id, input_type, result_json, created_at
            FROM pipeline_runs WHERE tenant_id = $1
            ORDER BY created_at DESC LIMIT 5
        """, tenant_id)
        recent = []
        for r in recent_rows:
            rj = r["result_json"]
            if isinstance(rj, str):
                rj = _json.loads(rj)
            recent.append({
                "cache_key": r["account_id"],
                "company_name": (rj or {}).get("company_profile", {}).get("name") or r["account_id"],
                "cached_at": r["created_at"].isoformat() if r["created_at"] else None,
                "input_type": r["input_type"],
            })

        # Top accounts by intent score
        top_rows = await conn.fetch("""
            SELECT DISTINCT ON (account_id)
                account_id,
                result_json->>'account_name' as account_name,
                (result_json->'intent'->>'score')::float as intent_score,
                result_json->'intent'->>'stage' as intent_stage
            FROM pipeline_runs WHERE tenant_id = $1
              AND result_json->'intent'->>'score' IS NOT NULL
            ORDER BY account_id, created_at DESC
        """, tenant_id)
        top_accounts = sorted(
            [dict(r) for r in top_rows if r["intent_score"]],
            key=lambda x: x["intent_score"] or 0, reverse=True
        )[:8]

        # Intent stage distribution
        stage_rows = await conn.fetch("""
            SELECT result_json->'intent'->>'stage' as stage, COUNT(*) as cnt
            FROM pipeline_runs WHERE tenant_id = $1
              AND result_json->'intent'->>'stage' IS NOT NULL
            GROUP BY stage
        """, tenant_id)
        intent_distribution = {r["stage"]: r["cnt"] for r in stage_rows}

        # Contacts count
        contacts_count = await conn.fetchval(
            "SELECT COUNT(*) FROM contacts WHERE tenant_id = $1", tenant_id
        )

    finally:
        await conn.close()

    return {
        "stats": {
            "total": sum(counts.values()),
            "visitors": counts.get("visitor_signal", 0),
            "companies": counts.get("company_seed", 0),
            "contacts": contacts_count or 0,
        },
        "recent_results": recent,
        "top_accounts": top_accounts,
        "intent_distribution": intent_distribution,
    }


class PushHubspotRequest(BaseModel):
    account_id: str


@router.post("/push-hubspot", summary="Push a company analysis result to HubSpot")
async def push_company_to_hubspot(
    body: PushHubspotRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import get_cached_result as db_get_cached
    from clients.hubspot_client import upsert_company
    from api.routes_hubspot_connection import get_hs_token

    result = await db_get_cached(tenant_id, body.account_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No analysis found for this account")

    cp = result.get("company_profile") or {}
    intent = result.get("intent") or {}
    icp = result.get("icp") or {}

    hs = await upsert_company(
        company_name=cp.get("name") or body.account_id,
        domain=cp.get("domain"),
        industry=cp.get("industry"),
        headquarters=cp.get("headquarters"),
        company_size=cp.get("employee_range") or cp.get("size"),
        ai_summary=cp.get("description") or cp.get("summary") or "",
        intent_score=float(intent.get("score") or 0),
        intent_stage=intent.get("stage") or "",
        recommended_action=(result.get("recommendations") or [{}])[0].get("action", "") if result.get("recommendations") else "",
        persona_label=icp.get("persona") or icp.get("label") or "",
        overall_confidence=float(result.get("confidence") or 0),
        token=await get_hs_token(tenant_id),
    )

    return {"success": hs.success, "hubspot_id": hs.external_id, "action": hs.action, "error": hs.error}


@router.get(
    "/health",
    summary="Analysis service health check",
)
async def health_check():
    """Health check for the analysis service."""
    return {
        "status": "healthy",
        "service": "analyze",
    }


# ── Visitor CRUD ──────────────────────────────────────────────────────────────

from pydantic import BaseModel

class VisitorCreateRequest(BaseModel):
    visitor_id: str
    ip_address: str = ""
    pages_visited: str = ""
    time_on_site_seconds: Optional[int] = None
    visits_this_week: Optional[int] = None
    referral_source: str = ""


@router.post("/visitors", summary="Save a visitor")
async def create_visitor(
    body: VisitorCreateRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import save_visitor
    await save_visitor(
        tenant_id, body.visitor_id, body.ip_address, body.pages_visited,
        body.time_on_site_seconds, body.visits_this_week, body.referral_source,
    )
    return {"status": "ok", "visitor_id": body.visitor_id}


@router.get("/visitors", summary="List visitors")
async def get_visitors(
    limit: int = Query(default=200, le=500),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import list_visitors
    visitors = await list_visitors(tenant_id, limit)
    return {"total": len(visitors), "visitors": visitors}

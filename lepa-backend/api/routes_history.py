"""
Account history API routes.

GET /accounts              — List all tracked accounts (from DB)
GET /accounts/{id}         — Get full history for one account
GET /accounts/{id}/audit   — Get confidence audit for latest run
GET /pipeline_runs        — List all pipeline runs (analysis history)
GET /jobs/{id}             — Get a single pipeline run
"""

import logging

from fastapi import APIRouter, Header, HTTPException, Query

logger = logging.getLogger("lepa.api.history")

router = APIRouter(tags=["history"])


@router.get(
    "/pipeline_runs",
    summary="List all pipeline runs",
    description="Returns all analysis runs across all accounts, most recent first.",
)
async def list_pipeline_runs(
    limit: int = Query(default=100, le=200),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from clients.db_client import list_pipeline_runs as _list_db
    from services.history import list_all_runs as _list_mem

    try:
        runs = await _list_db(tenant_id=tenant_id, limit=limit)
        return {"total": len(runs), "runs": runs}
    except Exception as e:
        logger.warning(f"Failed to fetch pipeline runs from DB: {e}")

    runs = _list_mem(limit=limit)
    return {"total": len(runs), "runs": runs}


@router.get(
    "/accounts",
    summary="List all tracked accounts",
    description="Returns all accounts that have been analyzed, sorted by most recently seen.",
)
async def list_accounts(
    limit: int = Query(default=50, le=100),
    search: str | None = Query(default=None),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    tenant_id = x_tenant_id or "default"
    from services.history import list_accounts as _list_mem
    from clients.db_client import list_accounts as _list_db

    # Get from DB first, fall back to in-memory
    try:
        db_accounts = await _list_db(tenant_id=tenant_id, limit=limit, search=search)
        return {
            "total": len(db_accounts),
            "accounts": [
                {
                    "account_id": a.get("account_id"),
                    "account_name": a.get("account_name"),
                    "domain": a.get("domain"),
                    "industry": a.get("industry"),
                    "visit_count_total": 0,
                    "first_seen_at": None,
                    "last_seen_at": None,
                    "latest_intent_score": a.get("confidence"),
                    "latest_intent_stage": a.get("input_type"),
                    "intent_direction": "unknown",
                    "run_count": 0,
                    "crm_sync_status": "unknown",
                }
                for a in db_accounts
            ],
        }
    except Exception:
        # Fallback to in-memory
        accounts = _list_mem(limit=limit)
        return {
            "total": len(accounts),
            "accounts": [
                {
                    "account_id": a.account_id,
                    "account_name": a.account_name,
                    "domain": a.domain,
                    "industry": a.industry,
                    "visit_count_total": a.visit_count_total,
                    "first_seen_at": a.first_seen_at,
                    "last_seen_at": a.last_seen_at,
                    "latest_intent_score": a.latest_intent.intent_score if a.latest_intent else None,
                    "latest_intent_stage": a.latest_intent.intent_stage if a.latest_intent else None,
                    "intent_direction": a.intent_direction,
                    "run_count": len(a.run_ids),
                    "crm_sync_status": a.crm_sync_status,
                }
                for a in accounts
            ],
        }


@router.get(
    "/accounts/{account_id}",
    summary="Get account history",
    description="Returns the full history for a single account including intent trend.",
)
async def get_account_history(account_id: str):
    from services.history import get_account

    account = get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    return {
        "account_id": account.account_id,
        "account_name": account.account_name,
        "domain": account.domain,
        "industry": account.industry,
        "visit_count_total": account.visit_count_total,
        "first_seen_at": account.first_seen_at,
        "last_seen_at": account.last_seen_at,
        "intent_direction": account.intent_direction,
        "intent_trend": [
            {
                "timestamp": snap.timestamp,
                "intent_score": snap.intent_score,
                "intent_stage": snap.intent_stage,
            }
            for snap in account.intent_trend
        ],
        "run_count": len(account.run_ids),
        "run_ids": account.run_ids,
        "crm_sync_status": account.crm_sync_status,
        "crm_provider": account.crm_provider,
        "crm_external_id": account.crm_external_id,
        "crm_synced_at": account.crm_synced_at,
    }


@router.get(
    "/jobs/{job_id}",
    summary="Get pipeline run status",
    description="Returns the status and events for a single pipeline run.",
)
async def get_job(job_id: str):
    from services.history import get_run

    run = get_run(job_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return {
        "job_id": run.job_id,
        "account_id": run.account_id,
        "input_type": run.input_type,
        "status": run.status,
        "batch_id": run.batch_id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "elapsed_seconds": run.elapsed_seconds,
        "error": run.error,
        "events": [
            {"type": e.type, "timestamp": e.timestamp, "detail": e.detail}
            for e in run.events
        ],
    }

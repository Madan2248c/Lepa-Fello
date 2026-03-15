"""
Account history service.

Maintains an in-memory registry of all analyzed accounts and their
historical intent trends, visit counts, and run records.

Also persists to Neon PostgreSQL for production durability.
"""

import re
from typing import Optional

from models.account_history import AccountHistory
from models.pipeline_run import PipelineRun, BatchRun
from schemas.output_models import AnalyzeResponse
from clients.db_client import save_account, save_pipeline_run


# ── In-memory stores ──────────────────────────────────────────────────────────

_accounts: dict[str, AccountHistory] = {}
_runs: dict[str, PipelineRun] = {}
_batches: dict[str, BatchRun] = {}


# ── Account ID derivation ─────────────────────────────────────────────────────

def _derive_account_id(result: AnalyzeResponse) -> str:
    """
    Derive a stable account_id from the analysis result.

    Priority: domain > normalized company name > input_id
    """
    if result.domain:
        clean = result.domain.lower().replace("www.", "").strip("/")
        return re.sub(r"[^a-z0-9\.\-]", "", clean)
    if result.account_name:
        return re.sub(r"[^a-z0-9]", "_", result.account_name.lower().strip())
    return re.sub(r"[^a-z0-9]", "_", result.input_id.lower().strip())


# ── Persistence ───────────────────────────────────────────────────────────────

def persist_result(result: AnalyzeResponse, run: PipelineRun, tenant_id: str = "default") -> AccountHistory:
    """
    Persist an analysis result into the account history store.

    Creates a new AccountHistory if the account has not been seen before,
    or updates the existing record with the latest run data.

    Args:
        result: The completed AnalyzeResponse from the pipeline.
        run: The PipelineRun tracking this execution.

    Returns:
        The updated AccountHistory record.
    """
    account_id = _derive_account_id(result)

    if account_id not in _accounts:
        _accounts[account_id] = AccountHistory(
            account_id=account_id,
            account_name=result.account_name,
            domain=result.domain,
            industry=result.industry,
        )

    history = _accounts[account_id]

    history.account_name = result.account_name or history.account_name
    history.domain = result.domain or history.domain
    history.industry = result.industry or history.industry

    visit_count = 1
    if result.input_type == "visitor_signal":
        for signal in result.key_signals_observed:
            if "visits this week" in signal.lower():
                try:
                    visit_count = int(signal.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass

    history.record_run(
        run_id=run.job_id,
        intent_score=result.intent.score,
        intent_stage=result.intent.stage,
        visit_count=visit_count,
    )

    run.account_id = account_id
    _runs[run.job_id] = run

    # Persist to Neon PostgreSQL
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(save_account(
            tenant_id=tenant_id,
            account_id=account_id,
            account_name=result.account_name,
            domain=result.domain,
            industry=result.industry,
        ), loop=loop)
        result_dict = result.model_dump(mode="json")
        asyncio.ensure_future(save_pipeline_run(
            tenant_id=tenant_id,
            account_id=account_id,
            input_type=result.input_type,
            result_json=result_dict,
            confidence=result.overall_confidence,
        ), loop=loop)
    except Exception as e:
        import logging
        logging.warning(f"Failed to persist to database: {e}")

    return history


def save_run(run: PipelineRun) -> None:
    """Save or update a pipeline run in the store."""
    _runs[run.job_id] = run


def save_batch(batch: BatchRun) -> None:
    """Save or update a batch run in the store."""
    _batches[batch.batch_id] = batch


# ── Retrieval ─────────────────────────────────────────────────────────────────

def get_account(account_id: str) -> Optional[AccountHistory]:
    return _accounts.get(account_id)


def list_accounts(limit: int = 50) -> list[AccountHistory]:
    accounts = list(_accounts.values())
    accounts.sort(key=lambda a: a.last_seen_at or a.first_seen_at or a.account_id, reverse=True)
    return accounts[:limit]


def get_run(job_id: str) -> Optional[PipelineRun]:
    return _runs.get(job_id)


def get_batch(batch_id: str) -> Optional[BatchRun]:
    return _batches.get(batch_id)


def list_runs_for_account(account_id: str) -> list[PipelineRun]:
    return [r for r in _runs.values() if r.account_id == account_id]


def list_all_runs(limit: int = 100) -> list[dict]:
    """List all pipeline runs from in-memory store, formatted for API response."""
    runs = list(_runs.values())
    runs.sort(key=lambda r: r.started_at or r.finished_at or r.job_id, reverse=True)
    result = []
    for r in runs[:limit]:
        acc = _accounts.get(r.account_id)
        result.append({
            "job_id": r.job_id,
            "account_id": r.account_id,
            "account_name": acc.account_name if acc else None,
            "input_type": r.input_type,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "elapsed_seconds": r.elapsed_seconds,
            "error": r.error,
        })
    return result

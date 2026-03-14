"""
Batch analysis API routes.

POST /batch/analyze  — Submit a list of companies for batch processing
GET  /batch/{id}     — Get batch run status and results
"""

import logging
from typing import Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from schemas.input_models import CompanySeedInput, VisitorSignalInput

logger = logging.getLogger("lepa.api.batch")

router = APIRouter(prefix="/batch", tags=["batch"])


class BatchAnalyzeRequest(BaseModel):
    """Request body for batch analysis."""

    companies: list[CompanySeedInput] = Field(
        default_factory=list,
        description="List of company seeds to analyze",
    )
    visitors: list[VisitorSignalInput] = Field(
        default_factory=list,
        description="List of visitor signals to analyze",
    )

    def all_items(self) -> list[Union[CompanySeedInput, VisitorSignalInput]]:
        return self.companies + self.visitors  # type: ignore[return-value]


class BatchItemSummary(BaseModel):
    index: int
    label: str
    job_id: str | None
    success: bool
    account_name: str | None = None
    domain: str | None = None
    intent_score: float | None = None
    intent_stage: str | None = None
    overall_confidence: float | None = None
    error: str | None = None


class BatchAnalyzeResponse(BaseModel):
    batch_id: str
    total: int
    completed: int
    failed: int
    status: str
    elapsed_seconds: float | None = None
    items: list[BatchItemSummary]


@router.post(
    "/analyze",
    response_model=BatchAnalyzeResponse,
    summary="Batch analyze multiple companies or visitors",
    description="""
Process multiple company seeds or visitor signals in one request.

- Accepts up to **10 items** per batch.
- Processes with bounded concurrency (3 at a time).
- Partial failures are captured per-item — the batch continues even if some items fail.
- Results are persisted to account history automatically.
    """,
)
async def batch_analyze(request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
    from services.batch_runner import run_batch

    items = request.all_items()

    if not items:
        raise HTTPException(status_code=400, detail="No items provided. Add companies or visitors.")

    if len(items) > 10:
        raise HTTPException(status_code=400, detail="Batch size limit is 10 items per request.")

    logger.info(f"Starting batch analysis: {len(items)} items")

    batch, item_results = await run_batch(items)

    summaries = []
    for item_result in item_results:
        if item_result is None:
            continue
        summary = BatchItemSummary(
            index=item_result.index,
            label=item_result.input_label,
            job_id=item_result.job_id,
            success=item_result.success,
            error=item_result.error,
        )
        if item_result.result:
            r = item_result.result
            summary.account_name = r.account_name
            summary.domain = r.domain
            summary.intent_score = r.intent.score
            summary.intent_stage = r.intent.stage
            summary.overall_confidence = r.overall_confidence
        summaries.append(summary)

    elapsed = None
    if batch.started_at and batch.finished_at:
        elapsed = round((batch.finished_at - batch.started_at).total_seconds(), 2)

    return BatchAnalyzeResponse(
        batch_id=batch.batch_id,
        total=batch.total,
        completed=batch.completed,
        failed=batch.failed,
        status=batch.status,
        elapsed_seconds=elapsed,
        items=summaries,
    )


@router.get(
    "/{batch_id}",
    summary="Get batch run status",
)
async def get_batch_status(batch_id: str):
    from services.history import get_batch

    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    return {
        "batch_id": batch.batch_id,
        "status": batch.status,
        "total": batch.total,
        "completed": batch.completed,
        "failed": batch.failed,
        "pending": batch.pending,
        "job_ids": batch.job_ids,
        "started_at": batch.started_at,
        "finished_at": batch.finished_at,
    }

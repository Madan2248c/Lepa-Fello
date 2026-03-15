"""
Batch analysis runner.

Accepts a list of company seeds or visitor signals and processes them
with bounded concurrency. Each record runs through the full Phase 1+2
pipeline independently. Partial failures do not abort the batch.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Union

from schemas.input_models import CompanySeedInput, VisitorSignalInput
from schemas.output_models import AnalyzeResponse
from models.pipeline_run import BatchRun, PipelineRun
from services.history import save_batch, save_run

logger = logging.getLogger("lepa.batch")

MAX_CONCURRENCY = 3


class BatchItemResult:
    """Result for a single item in a batch run."""

    def __init__(
        self,
        index: int,
        input_data: Union[CompanySeedInput, VisitorSignalInput],
        result: AnalyzeResponse | None = None,
        error: str | None = None,
        job_id: str | None = None,
    ):
        self.index = index
        self.input_label = (
            input_data.company_name
            if isinstance(input_data, CompanySeedInput)
            else input_data.visitor_id
        )
        self.result = result
        self.error = error
        self.job_id = job_id
        self.success = result is not None


async def run_batch(
    items: list[Union[CompanySeedInput, VisitorSignalInput]],
    batch_id: str | None = None,
    tenant_id: str = "default",
) -> tuple[BatchRun, list[BatchItemResult]]:
    """
    Process a list of company seeds or visitor signals as a batch.

    Uses a semaphore to limit concurrency to MAX_CONCURRENCY simultaneous
    pipeline runs. Each item is processed independently — failures are
    captured per-item and do not stop the batch.

    Args:
        items: List of CompanySeedInput or VisitorSignalInput objects.
        batch_id: Optional pre-assigned batch ID.

    Returns:
        Tuple of (BatchRun summary, list of BatchItemResult).
    """
    from services.pipeline import run_company_pipeline, run_visitor_pipeline

    batch = BatchRun(total=len(items), status="running")
    if batch_id:
        batch.batch_id = batch_id
    batch.started_at = datetime.now(timezone.utc)
    save_batch(batch)

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    item_results: list[BatchItemResult] = [None] * len(items)  # type: ignore[list-item]

    async def process_one(index: int, item: Union[CompanySeedInput, VisitorSignalInput]) -> None:
        async with semaphore:
            run = PipelineRun(
                account_id="pending",
                input_type="company_seed" if isinstance(item, CompanySeedInput) else "visitor_signal",
                batch_id=batch.batch_id,
            )
            run.start()
            save_run(run)
            batch.job_ids.append(run.job_id)

            try:
                if isinstance(item, CompanySeedInput):
                    result = await run_company_pipeline(item, tenant_id=tenant_id)
                else:
                    result = await run_visitor_pipeline(item, tenant_id=tenant_id)

                run.add_event("enriched")
                run.add_event("scored")
                run.add_event("summarized")
                run.complete()
                save_run(run)

                item_results[index] = BatchItemResult(
                    index=index,
                    input_data=item,
                    result=result,
                    job_id=run.job_id,
                )
                batch.completed += 1

                logger.info(
                    f"Batch {batch.batch_id} item {index + 1}/{batch.total} complete: "
                    f"{item_results[index].input_label}"
                )

            except Exception as e:
                error_msg = str(e)[:300]
                run.fail(error_msg)
                save_run(run)

                item_results[index] = BatchItemResult(
                    index=index,
                    input_data=item,
                    error=error_msg,
                    job_id=run.job_id,
                )
                batch.failed += 1

                logger.warning(
                    f"Batch {batch.batch_id} item {index + 1}/{batch.total} failed: {error_msg}"
                )

            save_batch(batch)

    await asyncio.gather(*[process_one(i, item) for i, item in enumerate(items)])

    batch.status = "failed" if batch.completed == 0 else "completed"
    batch.finished_at = datetime.now(timezone.utc)
    save_batch(batch)

    logger.info(
        f"Batch {batch.batch_id} finished: {batch.completed}/{batch.total} succeeded, "
        f"{batch.failed} failed"
    )

    return batch, item_results

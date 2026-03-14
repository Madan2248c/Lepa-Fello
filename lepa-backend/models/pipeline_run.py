"""
Pipeline run tracking models.

Tracks every analysis execution with status, timing, and output.
Uses an in-memory store (dict) for hackathon simplicity — no DB required.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field


RunStatus = Literal["queued", "running", "completed", "failed"]


class PipelineRunEvent(BaseModel):
    """A single timestamped event in a pipeline run."""

    type: Literal["ingested", "resolved", "enriched", "scored", "summarized", "exported"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detail: Optional[str] = None


class PipelineRun(BaseModel):
    """Tracks a single analysis execution."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    input_type: Literal["visitor_signal", "company_seed"]
    status: RunStatus = "queued"
    batch_id: Optional[str] = None

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None

    events: list[PipelineRunEvent] = Field(default_factory=list)

    def start(self) -> None:
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)
        self.events.append(PipelineRunEvent(type="ingested"))

    def complete(self) -> None:
        self.status = "completed"
        self.finished_at = datetime.now(timezone.utc)

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.finished_at = datetime.now(timezone.utc)
        self.error = error

    def add_event(self, event_type: PipelineRunEvent.__fields__["type"].annotation, detail: Optional[str] = None) -> None:  # type: ignore[name-defined]
        self.events.append(PipelineRunEvent(type=event_type, detail=detail))

    @property
    def elapsed_seconds(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class BatchRun(BaseModel):
    """Tracks a batch of pipeline runs."""

    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total: int = 0
    completed: int = 0
    failed: int = 0
    status: RunStatus = "queued"
    job_ids: list[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @property
    def pending(self) -> int:
        return self.total - self.completed - self.failed

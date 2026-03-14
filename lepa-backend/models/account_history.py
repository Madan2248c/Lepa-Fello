"""
Account history and CRM sync models.

Stores historical snapshots of account intelligence over time.
In-memory for hackathon; schema is designed to be portable to a DB later.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field


class IntentSnapshot(BaseModel):
    """A point-in-time intent score for trend tracking."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    intent_score: float
    intent_stage: Literal["Awareness", "Research", "Evaluation", "Decision"]


class AccountHistory(BaseModel):
    """
    Persistent record of an account across multiple analysis runs.

    account_id is derived from the domain (or company name if no domain).
    """

    account_id: str
    account_name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None

    visit_count_total: int = 0
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    intent_trend: list[IntentSnapshot] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)

    crm_sync_status: Literal["pending", "synced", "failed", "skipped", "not_attempted"] = "not_attempted"
    crm_provider: Optional[str] = None
    crm_external_id: Optional[str] = None
    crm_synced_at: Optional[datetime] = None

    def record_run(self, run_id: str, intent_score: float, intent_stage: str, visit_count: int = 1) -> None:
        now = datetime.now(timezone.utc)
        if not self.first_seen_at:
            self.first_seen_at = now
        self.last_seen_at = now
        self.visit_count_total += visit_count
        self.run_ids.append(run_id)
        self.intent_trend.append(
            IntentSnapshot(
                timestamp=now,
                intent_score=intent_score,
                intent_stage=intent_stage,  # type: ignore[arg-type]
            )
        )

    @property
    def latest_intent(self) -> Optional[IntentSnapshot]:
        return self.intent_trend[-1] if self.intent_trend else None

    @property
    def intent_direction(self) -> Literal["rising", "falling", "stable", "unknown"]:
        if len(self.intent_trend) < 2:
            return "unknown"
        delta = self.intent_trend[-1].intent_score - self.intent_trend[-2].intent_score
        if delta > 0.5:
            return "rising"
        if delta < -0.5:
            return "falling"
        return "stable"


class CrmSyncRecord(BaseModel):
    """Tracks a CRM sync attempt for an account."""

    sync_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    provider: Literal["hubspot", "salesforce", "none"]
    status: Literal["pending", "synced", "failed", "skipped"]
    external_record_id: Optional[str] = None
    error: Optional[str] = None
    attempted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synced_at: Optional[datetime] = None

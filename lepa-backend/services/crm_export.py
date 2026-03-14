"""
CRM export service.

Provider-agnostic abstraction for pushing account intelligence to a CRM.
Currently supports HubSpot. Salesforce can be added as a second provider
by implementing the same interface.

Sync status is persisted to the account history store.
"""

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from schemas.output_models import AnalyzeResponse
from models.account_history import CrmSyncRecord
from clients.hubspot_client import upsert_company

logger = logging.getLogger("lepa.crm")

CrmProvider = Literal["hubspot", "salesforce", "none"]


async def export_to_crm(
    result: AnalyzeResponse,
    account_id: str,
    provider: CrmProvider = "hubspot",
) -> CrmSyncRecord:
    """
    Export an account intelligence result to a CRM provider.

    Attempts the sync and returns a CrmSyncRecord with the outcome.
    The caller is responsible for persisting the record to account history.

    Args:
        result: The AnalyzeResponse to export.
        account_id: Internal account ID for tracking.
        provider: CRM provider to use ('hubspot' or 'salesforce').

    Returns:
        CrmSyncRecord with sync status and external record ID.
    """
    record = CrmSyncRecord(
        account_id=account_id,
        provider=provider,
        status="pending",
    )

    if provider == "none":
        record.status = "skipped"
        return record

    if provider == "salesforce":
        record.status = "skipped"
        record.error = "Salesforce integration not yet implemented — use HubSpot."
        return record

    if provider == "hubspot":
        return await _sync_to_hubspot(result, record)

    record.status = "failed"
    record.error = f"Unknown CRM provider: {provider}"
    return record


async def _sync_to_hubspot(
    result: AnalyzeResponse,
    record: CrmSyncRecord,
) -> CrmSyncRecord:
    """Sync an account to HubSpot and update the sync record."""
    first_action = (
        result.recommended_sales_action.actions[0]
        if result.recommended_sales_action.actions
        else result.recommended_sales_action.outreach_angle
    )

    logger.info(f"Exporting account '{result.account_name}' to HubSpot...")

    sync_result = await upsert_company(
        company_name=result.account_name or result.input_id,
        domain=result.domain,
        industry=result.industry,
        headquarters=result.headquarters,
        company_size=result.company_size,
        ai_summary=result.ai_summary,
        intent_score=result.intent.score,
        intent_stage=result.intent.stage,
        recommended_action=first_action,
        persona_label=result.persona.label,
        overall_confidence=result.overall_confidence,
    )

    if sync_result.success:
        record.status = "synced"
        record.external_record_id = sync_result.external_id
        record.synced_at = datetime.now(timezone.utc)
        logger.info(
            f"HubSpot sync succeeded for '{result.account_name}': "
            f"{sync_result.action} record {sync_result.external_id}"
        )
    else:
        record.status = "failed"
        record.error = sync_result.error
        logger.warning(f"HubSpot sync failed for '{result.account_name}': {sync_result.error}")

    return record


def apply_crm_sync_to_history(
    account_id: str,
    sync_record: CrmSyncRecord,
) -> None:
    """
    Update the account history store with the CRM sync result.

    Args:
        account_id: Internal account ID.
        sync_record: The completed CrmSyncRecord.
    """
    from services.history import get_account

    history = get_account(account_id)
    if not history:
        return

    history.crm_sync_status = sync_record.status
    history.crm_provider = sync_record.provider
    history.crm_external_id = sync_record.external_record_id
    history.crm_synced_at = sync_record.synced_at

"""
CRM export API routes.

POST /crm/export/{account_id}  — Push account to CRM
GET  /crm/status/{account_id}  — Check CRM sync status
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("lepa.api.crm")

router = APIRouter(prefix="/crm", tags=["crm"])


class CrmExportRequest(BaseModel):
    provider: Literal["hubspot", "salesforce"] = "hubspot"
    result_json: dict


class CrmExportResponse(BaseModel):
    account_id: str
    provider: str
    status: str
    external_id: str | None = None
    error: str | None = None
    action: str | None = None


@router.post(
    "/export/{account_id}",
    response_model=CrmExportResponse,
    summary="Export account to CRM",
    description="""
Push an analyzed account's intelligence to a CRM provider.

Provide the `result_json` from a previous `/analyze/company` or `/analyze/visitor` call.
The system will create or update a Company record in HubSpot with:
- Company name, domain, industry, HQ, size
- AI summary (as company description)
- Intent score, stage, persona
- Recommended sales action
- Overall confidence

**Requires**: `HUBSPOT_ACCESS_TOKEN` environment variable to be set.
    """,
)
async def export_to_crm(account_id: str, request: CrmExportRequest) -> CrmExportResponse:
    from schemas.output_models import AnalyzeResponse
    from services.crm_export import export_to_crm, apply_crm_sync_to_history

    try:
        result = AnalyzeResponse(**request.result_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid result_json: {str(e)[:200]}")

    sync_record = await export_to_crm(
        result=result,
        account_id=account_id,
        provider=request.provider,
    )

    apply_crm_sync_to_history(account_id, sync_record)

    return CrmExportResponse(
        account_id=account_id,
        provider=sync_record.provider,
        status=sync_record.status,
        external_id=sync_record.external_record_id,
        error=sync_record.error,
        action=None,
    )


@router.get(
    "/status/{account_id}",
    summary="Get CRM sync status for an account",
)
async def get_crm_status(account_id: str):
    from services.history import get_account

    account = get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    return {
        "account_id": account_id,
        "account_name": account.account_name,
        "crm_sync_status": account.crm_sync_status,
        "crm_provider": account.crm_provider,
        "crm_external_id": account.crm_external_id,
        "crm_synced_at": account.crm_synced_at,
    }

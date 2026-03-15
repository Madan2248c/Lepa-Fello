"""Tracker API key management."""
import secrets
from fastapi import APIRouter, Header

router = APIRouter(prefix="/tracker-keys", tags=["tracker"])


@router.get("")
async def list_keys(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")):
    from clients.db_client import list_tracker_keys
    tenant_id = x_tenant_id or "default"
    return {"keys": await list_tracker_keys(tenant_id)}


@router.post("")
async def create_key(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    from clients.db_client import create_tracker_key
    tenant_id = x_tenant_id or "default"
    api_key = f"lpk_{secrets.token_urlsafe(24)}"
    await create_tracker_key(tenant_id, api_key)
    return {"api_key": api_key}

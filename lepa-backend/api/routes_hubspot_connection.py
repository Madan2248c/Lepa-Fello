from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional
from clients.db_client import _connect

router = APIRouter()

class TokenBody(BaseModel):
    access_token: str

async def get_hs_token(tenant_id: str) -> Optional[str]:
    conn = await _connect()
    row = await conn.fetchrow("SELECT access_token FROM hubspot_connections WHERE tenant_id=$1", tenant_id)
    await conn.close()
    return row["access_token"] if row else None

@router.get("/hubspot/connection")
async def get_connection(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")):
    tenant_id = x_tenant_id or "default"
    conn = await _connect()
    row = await conn.fetchrow("SELECT access_token, created_at FROM hubspot_connections WHERE tenant_id=$1", tenant_id)
    await conn.close()
    if not row:
        return {"connected": False}
    t = row["access_token"]
    return {"connected": True, "token_preview": f"{t[:8]}...{t[-4:]}", "created_at": row["created_at"]}

@router.post("/hubspot/connection")
async def save_connection(body: TokenBody, x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")):
    tenant_id = x_tenant_id or "default"
    conn = await _connect()
    await conn.execute("""
        INSERT INTO hubspot_connections (tenant_id, access_token, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (tenant_id) DO UPDATE SET access_token=$2, updated_at=NOW()
    """, tenant_id, body.access_token)
    await conn.close()
    return {"ok": True}

@router.delete("/hubspot/connection")
async def delete_connection(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")):
    tenant_id = x_tenant_id or "default"
    conn = await _connect()
    await conn.execute("DELETE FROM hubspot_connections WHERE tenant_id=$1", tenant_id)
    await conn.close()
    return {"ok": True}

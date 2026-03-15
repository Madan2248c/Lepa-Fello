"""
Public tracking endpoint — receives events from tracker.js.
No auth header required; authenticated via API key in payload.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import Response

logger = logging.getLogger("lepa.api.tracker")
router = APIRouter(prefix="/track", tags=["tracker"])


@router.post("")
async def track_events(request: Request):
    import json
    from clients.db_client import (
        get_tenant_by_api_key,
        upsert_tracked_visitor,
        insert_tracker_events,
    )

    try:
        body = await request.body()
        payload = json.loads(body)
    except Exception:
        return Response(status_code=204)

    tenant_id = await get_tenant_by_api_key(payload.get("key", ""))
    if not tenant_id:
        return Response(status_code=204)

    ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-real-ip")
        or (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or None)
        or (request.client.host if request.client else None)
        or "unknown"
    )
    ua = request.headers.get("user-agent", "")

    await upsert_tracked_visitor(tenant_id, payload.get("vid", ""), ip, ua, payload.get("active_ms", 0))
    events = payload.get("events", [])
    active_ms = payload.get("active_ms", 0)
    # Stamp active_ms onto each event that doesn't have it
    for e in events:
        if not e.get("active_ms"):
            e["active_ms"] = active_ms
    if events:
        await insert_tracker_events(tenant_id, payload.get("vid", ""), payload.get("sid", ""), events)

    return Response(status_code=204)


@router.get("/visitors")
async def get_tracked_visitors(request: Request):
    from clients.db_client import list_tracked_visitors
    tenant_id = request.headers.get("x-tenant-id") or "default"
    visitors = await list_tracked_visitors(tenant_id)
    return {"total": len(visitors), "visitors": visitors}

"""
AI Assistant — conversational interface over tenant's LEPA data.
POST /assistant/chat  — streams SSE response
"""
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("lepa.api.assistant")
router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


async def _build_context(tenant_id: str) -> str:
    """Fetch a compact snapshot of tenant data to inject as context."""
    from clients.db_client import _connect
    conn = await _connect()
    try:
        accounts = await conn.fetch("""
            SELECT
                a.account_name, a.domain, a.industry,
                pr.result_json->'intent'->>'score' as intent_score,
                pr.result_json->'intent'->>'stage' as intent_stage,
                pr.result_json->>'overall_confidence' as confidence,
                pr.created_at
            FROM accounts a
            LEFT JOIN LATERAL (
                SELECT result_json, created_at FROM pipeline_runs
                WHERE tenant_id = $1 AND account_id = a.account_id
                ORDER BY created_at DESC LIMIT 1
            ) pr ON true
            WHERE a.tenant_id = $1
            ORDER BY (pr.result_json->'intent'->>'score')::float DESC NULLS LAST
            LIMIT 20
        """, tenant_id)

        contacts = await conn.fetch("""
            SELECT name, title, role, company_name, source_type
            FROM contacts WHERE tenant_id = $1
            ORDER BY created_at DESC LIMIT 30
        """, tenant_id)

        visitors = await conn.fetch("""
            SELECT ip_address, visit_count, total_active_ms, last_seen_at
            FROM tracked_visitors WHERE tenant_id = $1
            ORDER BY last_seen_at DESC LIMIT 10
        """, tenant_id)

    finally:
        await conn.close()

    lines = ["## Your LEPA Data Snapshot\n"]

    lines.append(f"### Accounts ({len(accounts)} shown, sorted by intent)")
    for a in accounts:
        lines.append(
            f"- {a['account_name'] or a['domain']} | industry: {a['industry'] or 'unknown'} "
            f"| intent: {a['intent_score']} ({a['intent_stage']})"
        )

    lines.append(f"\n### Contacts ({len(contacts)})")
    for c in contacts:
        lines.append(f"- {c['name']} | {c['title']} | {c['role']} | {c['company_name']}")

    lines.append(f"\n### Tracked Website Visitors ({len(visitors)})")
    for v in visitors:
        active_s = round((v['total_active_ms'] or 0) / 1000)
        lines.append(
            f"- IP: {v['ip_address']} | {v['visit_count']} visits | "
            f"{active_s}s active | last seen: {str(v['last_seen_at'])[:16]}"
        )

    return "\n".join(lines)


SYSTEM_PROMPT = """You are LEPA Assistant — an AI sales intelligence advisor embedded in the LEPA platform.
You have access to the user's real-time account data: companies being tracked, visitor signals, contacts, intent scores, and pipeline runs.

Your job:
- Answer questions about their data clearly and concisely
- Identify high-priority leads and explain why
- Suggest next actions (who to call, what to say, which accounts to prioritize)
- Help draft outreach messages when asked
- Spot patterns across accounts and visitors

Be direct, specific, and actionable. Reference actual company names, scores, and contacts from the data.
Format responses with bullet points and short paragraphs. Never make up data not in the context."""


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    tenant_id = request.headers.get("x-tenant-id") or "default"

    context = await _build_context(tenant_id)

    system = f"{SYSTEM_PROMPT}\n\n{context}"

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    from clients.bedrock_client import stream_claude

    def generate():
        try:
            for chunk in stream_claude(messages, system_prompt=system, model="haiku", max_tokens=1024):
                # SSE format
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Assistant stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

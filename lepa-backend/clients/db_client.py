"""
Database client for Neon PostgreSQL.
"""

import json
import logging
import os
from typing import Optional

import asyncpg

logger = logging.getLogger("lepa.db")

DATABASE_URL = os.getenv("NEON_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("NEON_DATABASE_URL environment variable is not set")


async def _connect():
    return await asyncpg.connect(DATABASE_URL)


async def save_account(tenant_id: str, account_id: str, account_name: Optional[str], domain: Optional[str], industry: Optional[str]):
    conn = await _connect()
    try:
        await conn.execute("""
            INSERT INTO accounts (tenant_id, account_id, account_name, domain, industry)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tenant_id, account_id) DO UPDATE
            SET account_name = EXCLUDED.account_name,
                domain = EXCLUDED.domain,
                industry = EXCLUDED.industry,
                updated_at = NOW()
        """, tenant_id, account_id, account_name, domain, industry)
    finally:
        await conn.close()


async def save_pipeline_run(tenant_id: str, account_id: str, input_type: str, result_json: dict, confidence: float):
    conn = await _connect()
    try:
        await conn.execute("""
            INSERT INTO pipeline_runs (tenant_id, account_id, input_type, result_json, confidence)
            VALUES ($1, $2, $3, $4::jsonb, $5)
        """, tenant_id, account_id, input_type, json.dumps(result_json), confidence)
    finally:
        await conn.close()


async def list_pipeline_runs(tenant_id: str, limit: int = 100):
    conn = await _connect()
    try:
        rows = await conn.fetch("""
            SELECT pr.id, pr.account_id, pr.input_type, pr.confidence, pr.created_at,
                   a.account_name
            FROM pipeline_runs pr
            LEFT JOIN accounts a ON a.tenant_id = pr.tenant_id AND a.account_id = pr.account_id
            WHERE pr.tenant_id = $1
            ORDER BY pr.created_at DESC
            LIMIT $2
        """, tenant_id, limit)
        return [
            {
                "job_id": f"run_{row['id']}",
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "input_type": row["input_type"] or "company_seed",
                "status": "completed",
                "started_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    finally:
        await conn.close()


async def get_cached_result(tenant_id: str, account_id: str) -> Optional[dict]:
    """Get the latest pipeline run result for an account."""
    conn = await _connect()
    try:
        row = await conn.fetchrow("""
            SELECT result_json FROM pipeline_runs
            WHERE tenant_id = $1 AND account_id = $2
              AND input_type IN ('visitor_signal', 'company_seed')
            ORDER BY created_at DESC LIMIT 1
        """, tenant_id, account_id)
        if not row:
            return None
        val = row["result_json"]
        return json.loads(val) if isinstance(val, str) else dict(val)
    finally:
        await conn.close()


async def list_accounts(tenant_id: str, limit: int = 100, search: str | None = None):
    conn = await _connect()
    try:
        if search:
            rows = await conn.fetch("""
                SELECT a.account_id, a.account_name, a.domain, a.industry,
                       p.input_type, p.confidence, p.created_at, p.result_json
                FROM accounts a
                LEFT JOIN LATERAL (
                    SELECT input_type, confidence, created_at, result_json
                    FROM pipeline_runs
                    WHERE tenant_id = a.tenant_id AND account_id = a.account_id
                    ORDER BY created_at DESC LIMIT 1
                ) p ON true
                WHERE a.tenant_id = $1
                  AND (a.account_name ILIKE $3 OR a.domain ILIKE $3)
                ORDER BY a.updated_at DESC LIMIT $2
            """, tenant_id, limit, f"%{search}%")
        else:
            rows = await conn.fetch("""
                SELECT a.account_id, a.account_name, a.domain, a.industry,
                       p.input_type, p.confidence, p.created_at, p.result_json
                FROM accounts a
                LEFT JOIN LATERAL (
                    SELECT input_type, confidence, created_at, result_json
                    FROM pipeline_runs
                    WHERE tenant_id = a.tenant_id AND account_id = a.account_id
                    ORDER BY created_at DESC LIMIT 1
                ) p ON true
                WHERE a.tenant_id = $1
                ORDER BY a.updated_at DESC LIMIT $2
            """, tenant_id, limit)
        return [dict(row) for row in rows]
    finally:
        await conn.close()


# ── ICP Profile ───────────────────────────────────────────────────────────────

async def save_icp_profile(tenant_id: str, target_industries: list, target_locations: list, target_company_sizes: list, target_roles: list):
    conn = await _connect()
    try:
        await conn.execute("""
            INSERT INTO icp_profiles (tenant_id, target_industries, target_locations, target_company_sizes, target_roles)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tenant_id) DO UPDATE
            SET target_industries = EXCLUDED.target_industries,
                target_locations = EXCLUDED.target_locations,
                target_company_sizes = EXCLUDED.target_company_sizes,
                target_roles = EXCLUDED.target_roles,
                updated_at = NOW()
        """, tenant_id, target_industries, target_locations, target_company_sizes, target_roles)
    finally:
        await conn.close()


async def get_icp_profile(tenant_id: str) -> Optional[dict]:
    conn = await _connect()
    try:
        row = await conn.fetchrow("SELECT * FROM icp_profiles WHERE tenant_id = $1", tenant_id)
        if row:
            return {
                "target_industries": list(row["target_industries"] or []),
                "target_locations": list(row["target_locations"] or []),
                "target_company_sizes": list(row["target_company_sizes"] or []),
                "target_roles": list(row["target_roles"] or []),
            }
        return None
    finally:
        await conn.close()


# ── Business Profile ──────────────────────────────────────────────────────────

async def save_business_profile(tenant_id: str, business_name: str, business_description: str, product_service: str, value_proposition: str):
    conn = await _connect()
    try:
        await conn.execute("""
            INSERT INTO business_profiles (tenant_id, business_name, business_description, product_service, value_proposition)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tenant_id) DO UPDATE
            SET business_name = EXCLUDED.business_name,
                business_description = EXCLUDED.business_description,
                product_service = EXCLUDED.product_service,
                value_proposition = EXCLUDED.value_proposition,
                updated_at = NOW()
        """, tenant_id, business_name, business_description, product_service, value_proposition)
    finally:
        await conn.close()


async def get_business_profile(tenant_id: str) -> Optional[dict]:
    conn = await _connect()
    try:
        row = await conn.fetchrow("SELECT * FROM business_profiles WHERE tenant_id = $1", tenant_id)
        return dict(row) if row else None
    finally:
        await conn.close()


# ── Contacts ──────────────────────────────────────────────────────────────────

async def upsert_contacts(tenant_id: str, contacts: list[dict]):
    """Upsert buying committee contacts from a pipeline run."""
    if not contacts:
        return
    conn = await _connect()
    try:
        for c in contacts:
            lp = c.get("linkedin_profile") or {}
            headline = lp.get("headline")
            about = lp.get("about_snippet")
            skills = lp.get("skills_sample") or []
            location = lp.get("location")
            scraped_at = "NOW()" if headline else None
            await conn.execute("""
                INSERT INTO contacts (
                    tenant_id, name, title, role, source_url, company_name, company_domain,
                    source_type, source_id,
                    linkedin_headline, linkedin_about, linkedin_skills, linkedin_location,
                    linkedin_scraped_at
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::text[],$13,
                    CASE WHEN $14 THEN NOW() ELSE NULL END)
                ON CONFLICT (tenant_id, name, company_domain) DO UPDATE
                SET title = EXCLUDED.title,
                    role = EXCLUDED.role,
                    source_url = COALESCE(EXCLUDED.source_url, contacts.source_url),
                    company_name = EXCLUDED.company_name,
                    source_type = EXCLUDED.source_type,
                    source_id = EXCLUDED.source_id,
                    linkedin_headline = COALESCE(EXCLUDED.linkedin_headline, contacts.linkedin_headline),
                    linkedin_about = COALESCE(EXCLUDED.linkedin_about, contacts.linkedin_about),
                    linkedin_skills = CASE WHEN $14 THEN EXCLUDED.linkedin_skills ELSE contacts.linkedin_skills END,
                    linkedin_location = COALESCE(EXCLUDED.linkedin_location, contacts.linkedin_location),
                    linkedin_scraped_at = CASE WHEN $14 THEN NOW() ELSE contacts.linkedin_scraped_at END
            """, tenant_id, c.get("name", ""), c.get("title", ""), c.get("role", ""),
                c.get("source_url"), c.get("company_name", ""), c.get("company_domain", ""),
                c.get("source_type", "company"), c.get("source_id", ""),
                headline, about, skills, location, headline is not None)
    finally:
        await conn.close()


async def list_contacts(tenant_id: str, limit: int = 200, search: str | None = None) -> list[dict]:
    conn = await _connect()
    try:
        if search:
            rows = await conn.fetch("""
                SELECT id, name, title, role, source_url, company_name, company_domain, source_type, source_id, created_at
                FROM contacts WHERE tenant_id = $1
                  AND (name ILIKE $3 OR company_name ILIKE $3 OR title ILIKE $3)
                ORDER BY created_at DESC LIMIT $2
            """, tenant_id, limit, f"%{search}%")
        else:
            rows = await conn.fetch("""
                SELECT id, name, title, role, source_url, company_name, company_domain, source_type, source_id, created_at
                FROM contacts WHERE tenant_id = $1
                ORDER BY created_at DESC LIMIT $2
            """, tenant_id, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_contact(tenant_id: str, contact_id: int) -> Optional[dict]:
    conn = await _connect()
    try:
        row = await conn.fetchrow("SELECT * FROM contacts WHERE tenant_id = $1 AND id = $2", tenant_id, contact_id)
        return dict(row) if row else None
    finally:
        await conn.close()


async def update_contact_linkedin(tenant_id: str, contact_id: int, headline: str, about: str, skills: list[str], location: str, personalized_email: str, personalized_linkedin_msg: str):
    conn = await _connect()
    try:
        from datetime import datetime, timezone
        await conn.execute("""
            UPDATE contacts SET
                linkedin_headline = $3, linkedin_about = $4, linkedin_skills = $5,
                linkedin_location = $6, linkedin_scraped_at = $7,
                personalized_email = $8, personalized_linkedin_msg = $9
            WHERE tenant_id = $1 AND id = $2
        """, tenant_id, contact_id, headline, about, skills, location,
            datetime.now(timezone.utc), personalized_email, personalized_linkedin_msg)
    finally:
        await conn.close()


async def update_contact_hubspot(tenant_id: str, contact_id: int, hubspot_id: str):
    conn = await _connect()
    try:
        from datetime import datetime, timezone
        await conn.execute("""
            UPDATE contacts SET hubspot_contact_id = $3, hubspot_synced_at = $4
            WHERE tenant_id = $1 AND id = $2
        """, tenant_id, contact_id, hubspot_id, datetime.now(timezone.utc))
    finally:
        await conn.close()


# ── Visitors ──────────────────────────────────────────────────────────────────

async def get_visitor_account_id(tenant_id: str, visitor_id: str) -> Optional[str]:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "SELECT resolved_account_id FROM visitors WHERE tenant_id = $1 AND visitor_id = $2",
            tenant_id, visitor_id
        )
        return row["resolved_account_id"] if row else None
    finally:
        await conn.close()


async def set_visitor_account_id(tenant_id: str, visitor_id: str, account_id: str):
    conn = await _connect()
    try:
        await conn.execute(
            "UPDATE visitors SET resolved_account_id = $1 WHERE tenant_id = $2 AND visitor_id = $3",
            account_id, tenant_id, visitor_id
        )
    finally:
        await conn.close()


async def save_visitor(tenant_id: str, visitor_id: str, ip_address: str, pages_visited: str, time_on_site_seconds: Optional[int], visits_this_week: Optional[int], referral_source: str):
    conn = await _connect()
    try:
        await conn.execute("""
            INSERT INTO visitors (tenant_id, visitor_id, ip_address, pages_visited, time_on_site_seconds, visits_this_week, referral_source)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (tenant_id, visitor_id) DO NOTHING
        """, tenant_id, visitor_id, ip_address, pages_visited, time_on_site_seconds, visits_this_week, referral_source)
    finally:
        await conn.close()


async def list_visitors(tenant_id: str, limit: int = 200) -> list[dict]:
    conn = await _connect()
    try:
        rows = await conn.fetch("""
            SELECT visitor_id as id, ip_address, pages_visited, time_on_site_seconds,
                   visits_this_week, referral_source, created_at
            FROM visitors WHERE tenant_id = $1
            ORDER BY created_at DESC LIMIT $2
        """, tenant_id, limit)
        return [
            {**dict(r), "created_at": r["created_at"].isoformat()}
            for r in rows
        ]
    finally:
        await conn.close()


# ── Tracker API keys ──────────────────────────────────────────────────────────

async def get_tenant_by_api_key(api_key: str) -> Optional[str]:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "SELECT tenant_id FROM tracker_keys WHERE api_key = $1 AND active = TRUE",
            api_key,
        )
        return row["tenant_id"] if row else None
    finally:
        await conn.close()


async def create_tracker_key(tenant_id: str, api_key: str, label: str = "default") -> None:
    conn = await _connect()
    try:
        await conn.execute("""
            INSERT INTO tracker_keys (tenant_id, api_key, label)
            VALUES ($1, $2, $3)
            ON CONFLICT (api_key) DO NOTHING
        """, tenant_id, api_key, label)
    finally:
        await conn.close()


async def list_tracker_keys(tenant_id: str) -> list[dict]:
    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT api_key, label, active, created_at FROM tracker_keys WHERE tenant_id = $1 ORDER BY created_at DESC",
            tenant_id,
        )
        return [{**dict(r), "created_at": r["created_at"].isoformat()} for r in rows]
    finally:
        await conn.close()


# ── Tracker events ────────────────────────────────────────────────────────────

async def upsert_tracked_visitor(tenant_id: str, vid: str, ip: str, user_agent: str, active_ms: int = 0) -> None:
    conn = await _connect()
    try:
        await conn.execute("""
            INSERT INTO tracked_visitors (tenant_id, vid, ip_address, user_agent, total_active_ms, last_seen_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (tenant_id, vid) DO UPDATE
              SET ip_address = EXCLUDED.ip_address,
                  user_agent = EXCLUDED.user_agent,
                  last_seen_at = NOW(),
                  visit_count = tracked_visitors.visit_count + 1,
                  total_active_ms = GREATEST(tracked_visitors.total_active_ms, $5)
        """, tenant_id, vid, ip, user_agent, active_ms)
    finally:
        await conn.close()


async def insert_tracker_events(tenant_id: str, vid: str, sid: str, events: list[dict]) -> None:
    conn = await _connect()
    try:
        await conn.executemany("""
            INSERT INTO tracker_events (tenant_id, vid, sid, event_type, url, referrer, active_ms)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, [
            (
                tenant_id, vid, sid,
                e.get("type", "pageview"),
                e.get("url", ""),
                e.get("ref", ""),
                e.get("active_ms"),
            )
            for e in events
        ])
    finally:
        await conn.close()


async def list_tracked_visitors(tenant_id: str, limit: int = 200) -> list[dict]:
    conn = await _connect()
    try:
        rows = await conn.fetch("""
            SELECT
                tv.vid, tv.ip_address, tv.user_agent, tv.visit_count,
                tv.total_active_ms, tv.last_seen_at,
                COUNT(te.id) AS event_count,
                array_agg(DISTINCT te.url ORDER BY te.url) FILTER (WHERE te.url IS NOT NULL AND te.url != '') AS pages
            FROM tracked_visitors tv
            LEFT JOIN tracker_events te ON te.tenant_id = tv.tenant_id AND te.vid = tv.vid
            WHERE tv.tenant_id = $1
            GROUP BY tv.vid, tv.ip_address, tv.user_agent, tv.visit_count, tv.total_active_ms, tv.last_seen_at
            ORDER BY tv.last_seen_at DESC
            LIMIT $2
        """, tenant_id, limit)
        return [
            {
                **dict(r),
                "last_seen_at": r["last_seen_at"].isoformat(),
                "pages": list(r["pages"] or []),
            }
            for r in rows
        ]
    finally:
        await conn.close()

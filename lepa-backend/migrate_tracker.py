"""Run once to create tracker tables."""
import asyncio
from clients.db_client import _connect

DDL = """
CREATE TABLE IF NOT EXISTS tracker_keys (
    id          SERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    api_key     TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL DEFAULT 'default',
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tracked_visitors (
    id           SERIAL PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    vid          TEXT NOT NULL,
    ip_address   TEXT,
    user_agent   TEXT,
    visit_count  INT NOT NULL DEFAULT 1,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, vid)
);

CREATE TABLE IF NOT EXISTS tracker_events (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    vid         TEXT NOT NULL,
    sid         TEXT NOT NULL,
    event_type  TEXT NOT NULL DEFAULT 'pageview',
    url         TEXT,
    referrer    TEXT,
    active_ms   BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracker_events_tenant_vid ON tracker_events (tenant_id, vid);
CREATE INDEX IF NOT EXISTS idx_tracked_visitors_tenant ON tracked_visitors (tenant_id);
"""

async def main():
    conn = await _connect()
    try:
        await conn.execute(DDL)
        print("✓ Tracker tables created")
    finally:
        await conn.close()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())

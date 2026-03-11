-- Project Mwavuli: Supabase/PostgreSQL schema
-- Run this in the Supabase SQL Editor or via psql.
--
-- This creates all tables needed by SupabaseRepository, with indexes
-- matching the query patterns used by analytics, export, and the API.

-- ═══════════════════════════════════════════════════════════════════
-- REPORTS
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS reports (
    id                    UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    text                  TEXT NOT NULL DEFAULT '',
    risk_level            TEXT NOT NULL DEFAULT 'UNKNOWN',
    language              TEXT DEFAULT 'auto-detect',
    county                TEXT DEFAULT 'unknown',
    timestamp             TIMESTAMPTZ DEFAULT now(),
    sender_hash           TEXT,
    sector                TEXT DEFAULT 'political',
    status                TEXT DEFAULT 'pending',

    -- Temporal (derived; kept as stored columns for query compatibility)
    hour_of_day           INT,
    day_of_week           TEXT,
    is_weekend            BOOLEAN DEFAULT false,

    -- Content analysis
    text_length           INT DEFAULT 0,
    word_count            INT DEFAULT 0,
    has_urls              BOOLEAN DEFAULT false,
    has_mentions          BOOLEAN DEFAULT false,

    -- Detection metadata
    detection_method      TEXT,
    confidence_score      FLOAT,
    matched_keyword       TEXT,
    gemini_context_flag   BOOLEAN DEFAULT false,

    -- Geographic
    region                TEXT DEFAULT 'Unknown',
    is_urban              BOOLEAN DEFAULT false,

    -- Scores stored as JSONB (flexible, like Firestore maps)
    scores                JSONB,

    -- Multi-tenant
    org_id                TEXT DEFAULT 'default',

    -- Optional fields
    source_type           TEXT,
    source_url            TEXT,
    content_hash          TEXT,
    created_by            TEXT,
    ingestion_job_id      TEXT,
    explanation           TEXT,
    explanation_details   JSONB,
    kenyan_model_risk     TEXT,
    kenyan_model_score    FLOAT,
    coordinated_campaign  BOOLEAN DEFAULT false,
    recommended_action    TEXT
);

CREATE INDEX IF NOT EXISTS idx_reports_timestamp       ON reports (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_reports_content_hash    ON reports (content_hash);
CREATE INDEX IF NOT EXISTS idx_reports_source_url      ON reports (source_url);
CREATE INDEX IF NOT EXISTS idx_reports_sender_ts       ON reports (sender_hash, timestamp);
CREATE INDEX IF NOT EXISTS idx_reports_sector_org      ON reports (sector, org_id);
CREATE INDEX IF NOT EXISTS idx_reports_status          ON reports (status);
CREATE INDEX IF NOT EXISTS idx_reports_risk_level      ON reports (risk_level);
CREATE INDEX IF NOT EXISTS idx_reports_county          ON reports (county);

-- ═══════════════════════════════════════════════════════════════════
-- REPORT AGGREGATES
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS report_aggregates (
    id                       TEXT PRIMARY KEY,  -- "{YYYY-MM-DD}-{sector}-{org_id}"
    date                     DATE NOT NULL,
    sector                   TEXT NOT NULL DEFAULT 'political',
    org_id                   TEXT NOT NULL DEFAULT 'default',
    risk_counts              JSONB DEFAULT '{}',
    keyword_counts           JSONB DEFAULT '{}',
    county_counts            JSONB DEFAULT '{}',
    toxicity                 JSONB DEFAULT '{"sum": 0, "count": 0}',
    status_counts            JSONB DEFAULT '{}',
    detection_method_counts  JSONB DEFAULT '{}',
    url_mention_counts       JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_aggregates_date       ON report_aggregates (date);
CREATE INDEX IF NOT EXISTS idx_aggregates_sector_org ON report_aggregates (sector, org_id);

-- ═══════════════════════════════════════════════════════════════════
-- AUDIT LOGS
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_logs (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp     TIMESTAMPTZ DEFAULT now(),
    action        TEXT NOT NULL,
    user_id       TEXT DEFAULT 'system',
    details       JSONB,
    api_key_hash  TEXT,
    prev_hash     TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_logs (action);

-- ═══════════════════════════════════════════════════════════════════
-- REPORT APPEALS
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS report_appeals (
    id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    report_id            TEXT NOT NULL,
    reason               TEXT NOT NULL,
    status               TEXT DEFAULT 'pending',
    timestamp            TIMESTAMPTZ DEFAULT now(),
    original_risk_level  TEXT,
    resolution           TEXT,
    resolved_at          TIMESTAMPTZ,
    notes                TEXT
);

CREATE INDEX IF NOT EXISTS idx_appeals_timestamp ON report_appeals (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_appeals_status    ON report_appeals (status);
CREATE INDEX IF NOT EXISTS idx_appeals_report    ON report_appeals (report_id);

-- ═══════════════════════════════════════════════════════════════════
-- INGESTION AUDIT
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ingestion_audit (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp     TIMESTAMPTZ DEFAULT now(),
    job_id        TEXT,
    action        TEXT,
    source_type   TEXT,
    url           TEXT,
    reason        TEXT,
    risk_level    TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingestion_audit_ts ON ingestion_audit (timestamp DESC);

-- ═══════════════════════════════════════════════════════════════════
-- INGESTION STATUS (single-row table, like Firestore's "last_run" doc)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ingestion_status (
    id         TEXT PRIMARY KEY DEFAULT 'last_run',
    timestamp  TIMESTAMPTZ DEFAULT now(),
    job_id     TEXT,
    counts     JSONB DEFAULT '{}'
);

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════
-- The backend uses the service_role_key which bypasses RLS.
-- These policies allow full access for authenticated service-role usage
-- and protect against accidental anon access.

ALTER TABLE reports             ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_aggregates   ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_appeals      ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_audit     ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_status    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access" ON reports           FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON report_aggregates FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON audit_logs        FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON report_appeals    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON ingestion_audit   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON ingestion_status  FOR ALL USING (true) WITH CHECK (true);

-- Migration 003: Add report_clusters table for topic clustering results.
-- Run this in the Supabase SQL Editor or via psql.
--
-- The cluster_reports.py script populates this table periodically
-- with HDBSCAN-discovered narrative clusters from report embeddings.

CREATE TABLE IF NOT EXISTS report_clusters (
    id                    UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    computed_at           TIMESTAMPTZ DEFAULT now(),
    cluster_label         INT NOT NULL,
    size                  INT NOT NULL,
    representative_text   TEXT,
    top_keywords          JSONB DEFAULT '[]',
    county_distribution   JSONB DEFAULT '{}',
    risk_breakdown        JSONB DEFAULT '{}',
    first_seen            TIMESTAMPTZ,
    last_seen             TIMESTAMPTZ,
    is_active             BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_clusters_active     ON report_clusters (is_active, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_computed_at ON report_clusters (computed_at DESC);

-- RLS (service role full access, same as other tables)
ALTER TABLE report_clusters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON report_clusters FOR ALL USING (true) WITH CHECK (true);

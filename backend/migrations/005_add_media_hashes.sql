-- Migration 005: Add media_hashes table for deduplication cache.
-- Run this in the Supabase SQL Editor or via psql.
--
-- When media is analyzed, its SHA-256 hash is stored alongside the result.
-- Subsequent requests for the same content return the cached result (0 API calls).

CREATE TABLE IF NOT EXISTS media_hashes (
    hash         TEXT PRIMARY KEY,
    risk_level   TEXT NOT NULL,
    explanation  TEXT,
    media_type   TEXT,
    analyzed_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_media_hashes_analyzed
    ON media_hashes (analyzed_at DESC);

-- RLS (service role full access, same as other tables)
ALTER TABLE media_hashes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON media_hashes FOR ALL USING (true) WITH CHECK (true);

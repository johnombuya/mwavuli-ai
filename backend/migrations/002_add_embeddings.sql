-- Migration 002: Add pgvector extension and embedding column to reports.
-- Run this in the Supabase SQL Editor or via psql.
--
-- The embedding column stores 384-dimensional vectors produced by
-- paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers).
-- Used for semantic similarity search and coordinated campaign detection.

-- Enable pgvector (built into Supabase, just needs activation)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to reports
ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS embedding vector(384);

-- IVFFlat index for fast cosine similarity queries.
-- Requires at least ~1000 rows before building; safe to run on empty table
-- (Postgres will use a sequential scan until enough rows exist).
CREATE INDEX IF NOT EXISTS idx_reports_embedding
    ON reports USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- RPC function used by detect_semantic_coordination() in the Python backend.
-- Returns reports whose embedding is within *similarity_threshold* cosine
-- distance of *query_embedding*, limited to the last *since_ts* window.
CREATE OR REPLACE FUNCTION match_similar_reports(
    query_embedding vector(384),
    similarity_threshold float DEFAULT 0.85,
    match_count int DEFAULT 50,
    since_ts timestamptz DEFAULT now() - interval '2 hours'
)
RETURNS TABLE (
    id uuid,
    sender_hash text,
    "text" text,
    risk_level text,
    "timestamp" timestamptz,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.sender_hash,
        r."text",
        r.risk_level,
        r."timestamp",
        1 - (r.embedding <=> query_embedding) AS similarity
    FROM reports r
    WHERE r.embedding IS NOT NULL
      AND r."timestamp" >= since_ts
      AND 1 - (r.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY r.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Migration 004: Add Gemini label columns for knowledge distillation.
-- Run this in the Supabase SQL Editor or via psql.
--
-- These columns store Gemini's auto-detected sector, county, and reasoning
-- so that future local models can be trained on this labeled data.

ALTER TABLE reports ADD COLUMN IF NOT EXISTS gemini_sector TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS gemini_county TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS gemini_reason TEXT;

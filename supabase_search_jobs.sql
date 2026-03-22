-- Run this in your Supabase SQL editor (Dashboard → SQL Editor)

CREATE TABLE IF NOT EXISTS search_jobs (
  id         SERIAL PRIMARY KEY,
  status     TEXT        NOT NULL DEFAULT 'pending',
  image_url  TEXT        NOT NULL,
  top_k      INTEGER     NOT NULL DEFAULT 30,
  results    JSONB,
  error      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Allow the service role (used by API routes) full access
ALTER TABLE search_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service role full access" ON search_jobs
  USING (true)
  WITH CHECK (true);

-- Also make sure the 'faces' storage bucket allows public reads
-- (needed so the CLI can download uploaded query images)
-- If it's already public, skip this.
-- UPDATE storage.buckets SET public = true WHERE name = 'faces';

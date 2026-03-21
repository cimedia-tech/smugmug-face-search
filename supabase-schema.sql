-- ============================================================
-- SmugMug Face Search — Supabase Schema
-- Run this in: Supabase Dashboard → SQL Editor
-- ============================================================

-- Drop incorrect tables from initial setup (they are empty, safe to drop)
DROP TABLE IF EXISTS face_people CASCADE;
DROP TABLE IF EXISTS faces CASCADE;
DROP TABLE IF EXISTS people CASCADE;
DROP TABLE IF EXISTS photos CASCADE;
DROP TABLE IF EXISTS albums CASCADE;
DROP TABLE IF EXISTS folders CASCADE;
DROP TABLE IF EXISTS index_runs CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Temporary OAuth state during the OAuth flow (replaces in-memory dict)
CREATE TABLE IF NOT EXISTS oauth_pending (
  request_token        TEXT PRIMARY KEY,
  request_token_secret TEXT NOT NULL,
  expires_at           TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '10 minutes')
);

-- Connected SmugMug account (enforced single row via id=1 check)
CREATE TABLE IF NOT EXISTS oauth_tokens (
  id                  INTEGER PRIMARY KEY CHECK (id = 1),
  access_token        TEXT NOT NULL,
  access_token_secret TEXT NOT NULL,
  smugmug_user        TEXT NOT NULL,
  saved_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Indexing job queue (CLI picks up pending jobs, UI tracks status)
CREATE TABLE IF NOT EXISTS indexing_jobs (
  id            BIGSERIAL PRIMARY KEY,
  status        TEXT NOT NULL DEFAULT 'pending',
  folder_path   TEXT,
  album_keys    TEXT[],
  total_images  INTEGER NOT NULL DEFAULT 0,
  indexed_count INTEGER NOT NULL DEFAULT 0,
  last_image_key TEXT,
  started_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  error         TEXT
);

-- Named groups of faces (created by clustering, named by user)
CREATE TABLE IF NOT EXISTS person_clusters (
  id             BIGSERIAL PRIMARY KEY,
  name           TEXT,
  sample_face_id BIGINT,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Core face index table
CREATE TABLE IF NOT EXISTS face_index (
  id                   BIGSERIAL PRIMARY KEY,
  smugmug_image_key    TEXT NOT NULL,
  album_key            TEXT,
  image_url            TEXT,
  thumbnail_url        TEXT,
  face_embedding       VECTOR(512),          -- NULL for images with no detected faces
  face_index_in_photo  INTEGER NOT NULL DEFAULT 0,
  bbox_x               REAL,
  bbox_y               REAL,
  bbox_w               REAL,
  bbox_h               REAL,
  face_crop_url        TEXT,                 -- Supabase Storage public URL
  cluster_id           BIGINT REFERENCES person_clusters(id),
  indexed_at           TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (smugmug_image_key, face_index_in_photo)
);

-- FK from person_clusters.sample_face_id → face_index.id
ALTER TABLE person_clusters
  ADD CONSTRAINT fk_sample_face
  FOREIGN KEY (sample_face_id) REFERENCES face_index(id)
  ON DELETE SET NULL
  DEFERRABLE INITIALLY DEFERRED;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_face_cluster   ON face_index(cluster_id);
CREATE INDEX IF NOT EXISTS idx_face_image_key ON face_index(smugmug_image_key);

-- View: people list with photo counts and sample face URL
CREATE OR REPLACE VIEW person_clusters_with_counts AS
SELECT
  pc.id,
  pc.name,
  pc.sample_face_id,
  fi_sample.face_crop_url AS sample_face_url,
  COUNT(fi.id)            AS photo_count
FROM person_clusters pc
LEFT JOIN face_index fi        ON fi.cluster_id = pc.id
LEFT JOIN face_index fi_sample ON fi_sample.id  = pc.sample_face_id
GROUP BY pc.id, pc.name, pc.sample_face_id, fi_sample.face_crop_url;

-- Disable RLS (single-user app, server-side service role key used for all DB access)
ALTER TABLE oauth_pending    DISABLE ROW LEVEL SECURITY;
ALTER TABLE oauth_tokens     DISABLE ROW LEVEL SECURITY;
ALTER TABLE indexing_jobs    DISABLE ROW LEVEL SECURITY;
ALTER TABLE person_clusters  DISABLE ROW LEVEL SECURITY;
ALTER TABLE face_index       DISABLE ROW LEVEL SECURITY;

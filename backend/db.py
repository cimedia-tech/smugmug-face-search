import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "faces.db")

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=5000;

            CREATE TABLE IF NOT EXISTS person_clusters (
                id INTEGER PRIMARY KEY,
                name TEXT,
                sample_face_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS face_index (
                id INTEGER PRIMARY KEY,
                smugmug_image_key TEXT NOT NULL,
                album_key TEXT,
                image_url TEXT,
                thumbnail_url TEXT,
                face_embedding BLOB NOT NULL,
                face_index_in_photo INTEGER DEFAULT 0,
                bbox_x REAL, bbox_y REAL, bbox_w REAL, bbox_h REAL,
                face_crop BLOB,
                cluster_id INTEGER REFERENCES person_clusters(id),
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_face_unique
                ON face_index(smugmug_image_key, face_index_in_photo);
            CREATE INDEX IF NOT EXISTS idx_face_cluster
                ON face_index(cluster_id);
            CREATE INDEX IF NOT EXISTS idx_face_image
                ON face_index(smugmug_image_key);

            CREATE TABLE IF NOT EXISTS indexing_jobs (
                id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                total_images INTEGER DEFAULT 0,
                indexed_count INTEGER DEFAULT 0,
                last_image_key TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS oauth_tokens (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                access_token TEXT,
                access_token_secret TEXT,
                smugmug_user TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

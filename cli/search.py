#!/usr/bin/env python3
"""
SmugMug Face Search — face similarity search CLI

Picks up pending search jobs from Supabase, extracts a face embedding from
the uploaded query image, computes cosine similarity against all indexed
faces, and writes the top matches back.

Usage:
  cd cli
  python search.py          # process one pending job then exit
  python search.py --watch  # loop forever, process jobs as they arrive
"""
import argparse
import asyncio
import json
import os
import sys
import time

import httpx
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from services.face_engine import extract_faces

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
TOP_K        = 30
PAGE_SIZE    = 1000


def sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_pending_job():
    r = sb().table('search_jobs').select('*').eq('status', 'pending') \
        .order('id', desc=False).limit(1).execute()
    return r.data[0] if r.data else None


def update_job(job_id: int, **kwargs):
    from datetime import datetime
    sb().table('search_jobs').update({
        **kwargs,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', job_id).execute()


def fetch_all_embeddings() -> list[dict]:
    """Fetch all indexed faces that have an embedding, paginated."""
    rows, start = [], 0
    while True:
        r = sb().table('face_index') \
            .select('id, smugmug_image_key, image_url, thumbnail_url, face_crop_url, face_embedding') \
            .not_.is_('face_embedding', 'null') \
            .range(start, start + PAGE_SIZE - 1) \
            .execute()
        batch = r.data or []
        rows.extend(batch)
        print(f"  Loaded {len(rows)} embeddings so far...")
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    return rows


def parse_embedding(raw) -> np.ndarray | None:
    """Handle embedding stored as list, string (JSON), or None."""
    if raw is None:
        return None
    try:
        if isinstance(raw, str):
            raw = json.loads(raw)
        arr = np.array(raw, dtype=np.float32)
        if arr.shape != (512,):
            return None
        return arr
    except Exception:
        return None


async def download_image(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=30)
        r.raise_for_status()
        return r.content


async def run_job(job: dict):
    job_id    = job['id']
    image_url = job['image_url']
    top_k     = job.get('top_k') or TOP_K

    update_job(job_id, status='running')
    print(f"Job {job_id}: downloading query image...")

    try:
        img_bytes = await download_image(image_url)
    except Exception as e:
        update_job(job_id, status='failed', error=f"Download failed: {e}")
        print(f"  Error: {e}")
        return

    print("  Extracting face embedding...")
    faces = extract_faces(img_bytes)
    if not faces:
        update_job(job_id, status='failed', error="No face detected in the uploaded image.")
        print("  No face found.")
        return

    # Use the largest/most prominent face (first returned)
    query_emb = np.array(faces[0]['embedding'], dtype=np.float32)
    query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-8)

    print("  Loading all indexed face embeddings...")
    rows = fetch_all_embeddings()
    if not rows:
        update_job(job_id, status='failed', error="No indexed faces found. Run indexing first.")
        return

    print(f"  Computing similarity across {len(rows)} faces...")
    embeddings, valid_rows = [], []
    for row in rows:
        emb = parse_embedding(row['face_embedding'])
        if emb is None:
            continue
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        embeddings.append(emb)
        valid_rows.append(row)

    if not embeddings:
        update_job(job_id, status='failed', error="No valid embeddings found.")
        return

    matrix    = np.stack(embeddings)                          # (N, 512)
    scores    = (matrix @ query_emb).tolist()                 # cosine similarity

    top_k_idx = np.argsort(scores)[::-1][:top_k]

    # Deduplicate by image key (keep best face per photo)
    seen_keys, results = set(), []
    for i in top_k_idx:
        row   = valid_rows[i]
        score = float(scores[i])
        key   = row['smugmug_image_key']
        if key in seen_keys:
            continue
        seen_keys.add(key)
        results.append({
            'image_key':    key,
            'image_url':    row.get('image_url'),
            'thumbnail_url': row.get('thumbnail_url'),
            'face_crop_url': row.get('face_crop_url'),
            'score':        round(score, 4),
        })

    update_job(job_id, status='done', results=results)
    print(f"  Done — {len(results)} matches found. Top score: {results[0]['score'] if results else 'n/a'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', action='store_true', help='Loop and process jobs as they arrive')
    args = parser.parse_args()

    while True:
        job = get_pending_job()
        if job:
            print(f"Picked up search job {job['id']}")
            asyncio.run(run_job(job))
        else:
            if not args.watch:
                print("No pending search jobs. Start a search from the web app first.")
                break
            print("Waiting for search jobs...")
            time.sleep(5)


if __name__ == '__main__':
    main()

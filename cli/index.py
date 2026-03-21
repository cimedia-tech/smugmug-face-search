#!/usr/bin/env python3
"""
SmugMug Face Search — local indexer CLI

Picks up a pending job from Supabase, downloads photos from SmugMug,
runs face detection locally using DeepFace, and writes results back to Supabase.

Usage:
  cd cli
  pip install -r requirements.txt
  cp .env.example .env   # fill in your keys
  python index.py
"""
import asyncio
import httpx
import json
import os
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ── Add backend to path so we can import face_engine ──────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from services.face_engine import extract_faces, is_processable_url

# ── Config ─────────────────────────────────────────────────────────────────
SUPABASE_URL    = os.environ["SUPABASE_URL"]
SUPABASE_KEY    = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SMUGMUG_KEY     = os.environ["SMUGMUG_API_KEY"]
SMUGMUG_SECRET  = os.environ["SMUGMUG_API_SECRET"]

DOWNLOAD_CONCURRENCY = int(os.environ.get("INDEX_CONCURRENCY",  "8"))
CPU_WORKERS          = int(os.environ.get("INDEX_CPU_WORKERS",  max(1, os.cpu_count() // 2)))

_executor: ProcessPoolExecutor | None = None


# ── Supabase helpers ────────────────────────────────────────────────────────

def sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_tokens():
    r = sb().table('oauth_tokens').select('*').eq('id', 1).single().execute()
    if not r.data:
        raise RuntimeError("No OAuth token found. Connect via the web app first.")
    return r.data['access_token'], r.data['access_token_secret'], r.data['smugmug_user']


def get_pending_job():
    r = sb().table('indexing_jobs').select('*').eq('status', 'pending').order('id', desc=True).limit(1).execute()
    return r.data[0] if r.data else None


def update_job(job_id: int, **kwargs):
    sb().table('indexing_jobs').update({
        **kwargs,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', job_id).execute()


def is_stop_requested(job_id: int) -> bool:
    r = sb().table('indexing_jobs').select('status').eq('id', job_id).single().execute()
    return bool(r.data and r.data['status'] == 'stop_requested')


def mark_interrupted():
    """Mark any jobs stuck in 'running' as 'interrupted' on startup."""
    sb().table('indexing_jobs').update({'status': 'interrupted'}).eq('status', 'running').execute()


def upload_crop(crop_bytes: bytes) -> str:
    """Upload a face crop JPEG to Supabase Storage. Returns the public URL."""
    filename = f"faces/{uuid.uuid4()}.jpg"
    sb().storage.from_('faces').upload(filename, crop_bytes, {'content-type': 'image/jpeg'})
    return f"{SUPABASE_URL}/storage/v1/object/public/faces/{filename}"


def already_indexed() -> set[str]:
    r = sb().table('face_index').select('smugmug_image_key').execute()
    return {row['smugmug_image_key'] for row in (r.data or [])}


def store_faces(image_key: str, album_key: str, image_url: str, thumb_url: str, faces: list):
    rows = []
    if not faces:
        rows.append({
            'smugmug_image_key':   image_key,
            'album_key':           album_key,
            'image_url':           image_url,
            'thumbnail_url':       thumb_url,
            'face_embedding':      None,
            'face_index_in_photo': -1,
        })
    else:
        for fi, face in enumerate(faces):
            crop_url = None
            if face.get('crop_bytes'):
                try:
                    crop_url = upload_crop(face['crop_bytes'])
                except Exception as e:
                    print(f"  Crop upload failed: {e}")

            rows.append({
                'smugmug_image_key':   image_key,
                'album_key':           album_key,
                'image_url':           image_url,
                'thumbnail_url':       thumb_url,
                'face_embedding':      face['embedding'],   # list of 512 floats
                'face_index_in_photo': fi,
                'bbox_x':              face['bbox']['x'],
                'bbox_y':              face['bbox']['y'],
                'bbox_w':              face['bbox']['w'],
                'bbox_h':              face['bbox']['h'],
                'face_crop_url':       crop_url,
            })

    sb().table('face_index').upsert(rows, on_conflict='smugmug_image_key,face_index_in_photo').execute()


# ── SmugMug helpers ─────────────────────────────────────────────────────────

import time
from requests_oauthlib import OAuth1Session

SMUGMUG_BASE = "https://api.smugmug.com"


def smug_client(token, secret):
    return OAuth1Session(SMUGMUG_KEY, client_secret=SMUGMUG_SECRET,
                         resource_owner_key=token, resource_owner_secret=secret)


def smug_get(session, path, params=None):
    p = {"_accept": "application/json", **(params or {})}
    time.sleep(0.2)
    r = session.get(SMUGMUG_BASE + path, params=p)
    r.raise_for_status()
    return r.json()["Response"]


def get_images(session, album_key: str) -> list:
    images, start = [], 1
    while True:
        try:
            data = smug_get(session, f"/api/v2/album/{album_key}!images",
                            {"start": start, "count": 100})
        except Exception as e:
            print(f"  Skipping album {album_key}: {e}")
            break
        images.extend(data.get("AlbumImage", []))
        if not data.get("Pages", {}).get("NextPage"):
            break
        start += 100
    return images


def get_all_albums(session, user: str, folder_path: str | None, album_keys: list | None) -> list:
    if album_keys:
        return [{"AlbumKey": k} for k in album_keys]
    if folder_path:
        return get_albums_in_folder(session, user, folder_path)
    # All albums
    albums, start = [], 1
    while True:
        data = smug_get(session, f"/api/v2/user/{user}!albums", {"start": start, "count": 100})
        albums.extend(data.get("Album", []))
        if not data.get("Pages", {}).get("NextPage"):
            break
        start += 100
    return albums


def get_albums_in_folder(session, user, folder_path):
    def _folder_albums(path):
        p = f"/api/v2/folder/user/{user}/{path.strip('/')}!albums"
        try:
            return smug_get(session, p).get("Album", [])
        except Exception:
            return []

    def _subfolders(path):
        p = f"/api/v2/folder/user/{user}/{path.strip('/')}!folders"
        try:
            return smug_get(session, p).get("Folder", [])
        except Exception:
            return []

    albums = _folder_albums(folder_path)
    for sub in _subfolders(folder_path):
        url = sub.get("UrlPath", "")
        prefix = f"/user/{user}/"
        rel = url[len(prefix):] if url.startswith(prefix) else url.lstrip("/")
        if rel:
            albums.extend(get_albums_in_folder(session, user, rel))
    return albums


def sized_url(img: dict) -> str:
    for size in ["X3LargeImageUrl", "X2LargeImageUrl", "LargeImageUrl", "ImageUrl"]:
        if img.get(size):
            return img[size]
    return img.get("ArchivedUri", "")


# ── Worker init (pre-loads DeepFace model per process) ──────────────────────

def _worker_init():
    from services.face_engine import preload_models
    preload_models()


def get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=CPU_WORKERS, initializer=_worker_init)
    return _executor


# ── Main indexing loop ──────────────────────────────────────────────────────

async def run(job: dict):
    token, secret, user = get_tokens()
    session = smug_client(token, secret)
    loop    = asyncio.get_event_loop()
    executor = get_executor()

    job_id      = job['id']
    folder_path = job.get('folder_path')
    album_keys  = job.get('album_keys')

    update_job(job_id, status='running')
    print(f"Job {job_id} started — scope: folder={folder_path}, albums={album_keys}")

    # Collect all images
    print("Fetching album list...")
    albums = get_all_albums(session, user, folder_path, album_keys)
    all_images = []
    for album in albums:
        imgs = get_images(session, album["AlbumKey"])
        all_images.extend((img, album["AlbumKey"]) for img in imgs)

    print(f"Found {len(all_images)} images across {len(albums)} albums")
    update_job(job_id, total_images=len(all_images))

    indexed_set = already_indexed()
    sem         = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)
    processed   = 0

    async def process_one(http: httpx.AsyncClient, img: dict, album_key: str):
        nonlocal processed
        image_key  = img.get("ImageKey", "")
        image_url  = sized_url(img)
        thumb_url  = img.get("ThumbnailUrl", "")

        if image_key in indexed_set:
            processed += 1
            update_job(job_id, indexed_count=processed)
            return

        if not is_processable_url(image_url):
            indexed_set.add(image_key)
            processed += 1
            update_job(job_id, indexed_count=processed)
            return

        async with sem:
            try:
                resp = await http.get(image_url, timeout=30)
                resp.raise_for_status()
                faces = await loop.run_in_executor(executor, extract_faces, resp.content)
                store_faces(image_key, album_key, image_url, thumb_url, faces)
                indexed_set.add(image_key)
            except Exception as e:
                print(f"  Skip {image_key}: {e}")

        processed += 1
        update_job(job_id, indexed_count=processed, last_image_key=image_key)

        if processed % 50 == 0:
            print(f"  {processed}/{len(all_images)} ({processed*100//len(all_images)}%)")
            if is_stop_requested(job_id):
                raise asyncio.CancelledError("Stop requested")

    async with httpx.AsyncClient() as http:
        tasks = [asyncio.create_task(process_one(http, img, ak)) for img, ak in all_images]
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

    if is_stop_requested(job_id):
        update_job(job_id, status='stopped')
        print(f"Job {job_id} stopped at {processed}/{len(all_images)}")
    else:
        update_job(job_id, status='done')
        print(f"Job {job_id} complete — {processed} images processed")


def main():
    mark_interrupted()

    job = get_pending_job()
    if not job:
        print("No pending job found.")
        print("Start indexing via the web UI first, then run this script.")
        return

    print(f"Picked up job {job['id']}")
    asyncio.run(run(job))


if __name__ == '__main__':
    main()

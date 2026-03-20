import asyncio
import httpx
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from db import get_conn
from services.smugmug import SmugMugClient
from services.face_engine import extract_faces, embedding_to_blob, is_processable_url

# Number of parallel download streams
DOWNLOAD_CONCURRENCY = int(os.environ.get("INDEX_CONCURRENCY", "8"))

# Number of CPU worker processes for face detection (default: half of cores)
CPU_WORKERS = int(os.environ.get("INDEX_CPU_WORKERS", max(1, os.cpu_count() // 2)))

# Stop flag
_stop_requested: int | None = None
_executor: ProcessPoolExecutor | None = None


def get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(
            max_workers=CPU_WORKERS,
            initializer=_worker_init,
        )
    return _executor


def _worker_init():
    """Called once per worker process — pre-loads the DeepFace model."""
    from services.face_engine import preload_models
    preload_models()


def request_stop(job_id: int):
    global _stop_requested
    _stop_requested = job_id


def _get_tokens():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM oauth_tokens WHERE id=1").fetchone()
        if not row:
            return None, None, None
        return row["access_token"], row["access_token_secret"], row["smugmug_user"]


def _create_job() -> int:
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO indexing_jobs(status) VALUES('pending')")
        return cur.lastrowid


def _update_job(job_id: int, **kwargs):
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [job_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE indexing_jobs SET {sets} WHERE id=?", vals)


def get_active_job():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM indexing_jobs ORDER BY id DESC LIMIT 1"
        ).fetchone()


def _sized_url(img: dict) -> str:
    for size in ["X3LargeImageUrl", "X2LargeImageUrl", "LargeImageUrl", "ImageUrl"]:
        url = img.get(size)
        if url:
            return url
    return img.get("ArchivedUri", "")


def _store_faces_batch(image_key: str, album_key: str, image_url: str,
                       thumb_url: str, faces: list):
    if not faces:
        with get_conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO face_index
                (smugmug_image_key, album_key, image_url, thumbnail_url,
                 face_embedding, face_index_in_photo, bbox_x, bbox_y, bbox_w, bbox_h, face_crop)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (image_key, album_key, image_url, thumb_url,
                  b'\x00' * 4, -1, 0, 0, 0, 0, None))
        return

    rows = [
        (image_key, album_key, image_url, thumb_url,
         embedding_to_blob(f["embedding"]), fi,
         f["bbox"]["x"], f["bbox"]["y"], f["bbox"]["w"], f["bbox"]["h"],
         f["crop_bytes"])
        for fi, f in enumerate(faces)
    ]
    with get_conn() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO face_index
            (smugmug_image_key, album_key, image_url, thumbnail_url,
             face_embedding, face_index_in_photo, bbox_x, bbox_y, bbox_w, bbox_h, face_crop)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, rows)


def _resolve_albums(client, user, folder_path, album_keys):
    if album_keys:
        return [{"AlbumKey": k} for k in album_keys]
    if folder_path:
        return client.get_albums_in_folder(user, folder_path)
    return client.get_albums(user)


async def run_indexing(job_id: int, folder_path=None, album_keys=None):
    global _stop_requested
    token, secret, user = _get_tokens()
    if not token:
        _update_job(job_id, status="failed", error="No OAuth token stored")
        return

    client = SmugMugClient(
        os.environ["SMUGMUG_API_KEY"], os.environ["SMUGMUG_API_SECRET"], token, secret
    )

    loop = asyncio.get_event_loop()
    executor = get_executor()

    try:
        albums = _resolve_albums(client, user, folder_path, album_keys)
        all_images = []
        for album in albums:
            imgs = client.get_images(album["AlbumKey"])
            for img in imgs:
                all_images.append((img, album["AlbumKey"]))

        _update_job(job_id, status="running", total_images=len(all_images))

        with get_conn() as conn:
            already_indexed = set(
                r[0] for r in conn.execute(
                    "SELECT DISTINCT smugmug_image_key FROM face_index"
                ).fetchall()
            )

        sem = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)
        processed = 0

        async def process_one(http: httpx.AsyncClient, img: dict, album_key: str):
            nonlocal processed

            image_key = img.get("ImageKey", "")
            image_url = _sized_url(img)
            thumb_url = img.get("ThumbnailUrl", "")

            if image_key in already_indexed:
                processed += 1
                _update_job(job_id, indexed_count=processed)
                return

            # Skip non-image files (videos, raw, etc.)
            if not is_processable_url(image_url):
                already_indexed.add(image_key)
                processed += 1
                _update_job(job_id, indexed_count=processed)
                return

            async with sem:
                try:
                    resp = await http.get(image_url, timeout=30)
                    resp.raise_for_status()
                    # Offload CPU-bound detection to a worker process (true parallelism)
                    faces = await loop.run_in_executor(executor, extract_faces, resp.content)
                    _store_faces_batch(image_key, album_key, image_url, thumb_url, faces)
                    already_indexed.add(image_key)
                except Exception as e:
                    print(f"Skip {image_key}: {e}")

            processed += 1
            _update_job(job_id, indexed_count=processed, last_image_key=image_key)

        async with httpx.AsyncClient() as http:
            tasks = []
            for img, album_key in all_images:
                if _stop_requested == job_id:
                    break
                tasks.append(asyncio.create_task(process_one(http, img, album_key)))

            await asyncio.gather(*tasks, return_exceptions=True)

        if _stop_requested == job_id:
            _stop_requested = None
            _update_job(job_id, status="stopped")
        else:
            _update_job(job_id, status="done")

    except Exception as e:
        _update_job(job_id, status="failed", error=str(e))


def start_indexing_job(folder_path=None, album_keys=None) -> int:
    job_id = _create_job()
    asyncio.create_task(run_indexing(job_id, folder_path=folder_path, album_keys=album_keys))
    return job_id

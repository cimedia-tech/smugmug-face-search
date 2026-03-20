import asyncio
import httpx
import os
from datetime import datetime
from db import get_conn
from services.smugmug import SmugMugClient
from services.face_engine import extract_faces, embedding_to_blob

# How many images to download concurrently while processing
DOWNLOAD_CONCURRENCY = int(os.environ.get("INDEX_CONCURRENCY", "4"))

# Stop flag — set to current job_id to request cancellation
_stop_requested: int | None = None


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
    """Use a smaller sized URL instead of full-res ArchivedUri."""
    for size in ["X3LargeImageUrl", "X2LargeImageUrl", "LargeImageUrl", "ImageUrl"]:
        url = img.get(size)
        if url:
            return url
    return img.get("ArchivedUri", "")


def _store_faces_batch(image_key: str, album_key: str, image_url: str,
                       thumb_url: str, faces: list):
    """Insert all faces for one image in a single transaction."""
    if not faces:
        # Still record that this image was processed (0 faces)
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


def _resolve_albums(client: SmugMugClient, user: str,
                    folder_path: str | None, album_keys: list[str] | None) -> list[dict]:
    if album_keys:
        return [{"AlbumKey": k} for k in album_keys]
    if folder_path:
        return client.get_albums_in_folder(user, folder_path)
    return client.get_albums(user)


async def run_indexing(job_id: int, folder_path: str | None = None,
                       album_keys: list[str] | None = None):
    global _stop_requested
    token, secret, user = _get_tokens()
    if not token:
        _update_job(job_id, status="failed", error="No OAuth token stored")
        return

    client = SmugMugClient(
        os.environ["SMUGMUG_API_KEY"], os.environ["SMUGMUG_API_SECRET"], token, secret
    )

    try:
        albums = _resolve_albums(client, user, folder_path, album_keys)
        all_images = []
        for album in albums:
            imgs = client.get_images(album["AlbumKey"])
            for img in imgs:
                all_images.append((img, album["AlbumKey"]))

        _update_job(job_id, status="running", total_images=len(all_images))

        # Load already-indexed keys once
        with get_conn() as conn:
            already_indexed = set(
                r[0] for r in conn.execute(
                    "SELECT DISTINCT smugmug_image_key FROM face_index"
                ).fetchall()
            )

        # Semaphore limits concurrent downloads
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

            async with sem:
                try:
                    resp = await http.get(image_url, timeout=30)
                    resp.raise_for_status()
                    faces = await asyncio.to_thread(extract_faces, resp.content)
                    _store_faces_batch(image_key, album_key, image_url, thumb_url, faces)
                    already_indexed.add(image_key)
                except Exception as e:
                    print(f"Skip {image_key}: {e}")

            processed += 1
            _update_job(job_id, indexed_count=processed, last_image_key=image_key)

        async with httpx.AsyncClient() as http:
            tasks = []
            for img, album_key in all_images:
                # Check stop flag before queuing each batch
                if _stop_requested == job_id:
                    _stop_requested = None
                    _update_job(job_id, status="stopped")
                    # Cancel pending tasks
                    for t in tasks:
                        t.cancel()
                    return
                tasks.append(asyncio.create_task(process_one(http, img, album_key)))

            await asyncio.gather(*tasks, return_exceptions=True)

        if _stop_requested == job_id:
            _stop_requested = None
            _update_job(job_id, status="stopped")
        else:
            _update_job(job_id, status="done")

    except Exception as e:
        _update_job(job_id, status="failed", error=str(e))


def start_indexing_job(folder_path: str | None = None,
                       album_keys: list[str] | None = None) -> int:
    job_id = _create_job()
    asyncio.create_task(run_indexing(job_id, folder_path=folder_path, album_keys=album_keys))
    return job_id

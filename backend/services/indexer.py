import asyncio
import httpx
from datetime import datetime
from db import get_conn
from services.smugmug import SmugMugClient
from services.face_engine import extract_faces, embedding_to_blob
import os

API_KEY = os.environ.get("SMUGMUG_API_KEY", "")
API_SECRET = os.environ.get("SMUGMUG_API_SECRET", "")

def _get_tokens():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM oauth_tokens WHERE id=1").fetchone()
        if not row:
            return None, None, None
        return row["access_token"], row["access_token_secret"], row["smugmug_user"]

def _create_job() -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO indexing_jobs(status) VALUES('pending')"
        )
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

def _already_indexed(image_key: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM face_index WHERE smugmug_image_key=? LIMIT 1",
            (image_key,)
        ).fetchone()
        return row is not None

def _store_face(image_key: str, album_key: str, image_url: str,
                thumb_url: str, face_idx: int, emb, bbox: dict, crop: bytes):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO face_index
            (smugmug_image_key, album_key, image_url, thumbnail_url,
             face_embedding, face_index_in_photo, bbox_x, bbox_y, bbox_w, bbox_h, face_crop)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (image_key, album_key, image_url, thumb_url,
              embedding_to_blob(emb), face_idx,
              bbox["x"], bbox["y"], bbox["w"], bbox["h"],
              crop))

def _resolve_albums(client: SmugMugClient, user: str,
                    folder_path: str | None, album_keys: list[str] | None) -> list[dict]:
    """Return list of album dicts based on the requested scope."""
    if album_keys:
        # Specific albums by key — wrap in minimal dicts
        return [{"AlbumKey": k} for k in album_keys]
    if folder_path:
        return client.get_albums_in_folder(user, folder_path)
    # No scope = full account
    return client.get_albums(user)


async def run_indexing(job_id: int, folder_path: str | None = None,
                       album_keys: list[str] | None = None):
    token, secret, user = _get_tokens()
    if not token:
        _update_job(job_id, status="failed", error="No OAuth token stored")
        return

    client = SmugMugClient(API_KEY, API_SECRET, token, secret)

    scope_label = folder_path or ("selected albums" if album_keys else "full account")

    try:
        albums = _resolve_albums(client, user, folder_path, album_keys)
        all_images = []
        for album in albums:
            imgs = client.get_images(album["AlbumKey"])
            for img in imgs:
                all_images.append((img, album["AlbumKey"]))

        _update_job(job_id, status="running", total_images=len(all_images))

        # Load already-indexed keys once to avoid per-image DB queries
        with get_conn() as conn:
            already_indexed = set(
                r[0] for r in conn.execute(
                    "SELECT smugmug_image_key FROM face_index"
                ).fetchall()
            )

        async with httpx.AsyncClient(timeout=30) as http:
            for i, (img, album_key) in enumerate(all_images):
                image_key = img.get("ImageKey", "")
                image_url = img.get("ArchivedUri") or img.get("ImageUrl", "")
                thumb_url = img.get("ThumbnailUrl", "")

                if image_key in already_indexed:
                    _update_job(job_id, indexed_count=i+1, last_image_key=image_key)
                    continue

                try:
                    resp = await http.get(image_url)
                    resp.raise_for_status()
                    faces = await asyncio.to_thread(extract_faces, resp.content)
                    for fi, face in enumerate(faces):
                        _store_face(image_key, album_key, image_url, thumb_url,
                                    fi, face["embedding"], face["bbox"], face["crop_bytes"])
                    already_indexed.add(image_key)
                except Exception as e:
                    print(f"Skip {image_key}: {e}")

                _update_job(job_id, indexed_count=i+1, last_image_key=image_key)

        _update_job(job_id, status="done")
    except Exception as e:
        _update_job(job_id, status="failed", error=str(e))


def start_indexing_job(folder_path: str | None = None,
                       album_keys: list[str] | None = None) -> int:
    job_id = _create_job()
    asyncio.create_task(run_indexing(job_id, folder_path=folder_path, album_keys=album_keys))
    return job_id

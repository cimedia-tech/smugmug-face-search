"""
Endpoints for browsing the SmugMug folder/album tree so the UI can
let the user pick a scope before indexing.
"""
import os
from fastapi import APIRouter, HTTPException, Query
from db import get_conn
from services.smugmug import SmugMugClient

router = APIRouter(prefix="/browse")

API_KEY = os.environ.get("SMUGMUG_API_KEY", "")
API_SECRET = os.environ.get("SMUGMUG_API_SECRET", "")


def _client():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM oauth_tokens WHERE id=1").fetchone()
    if not row:
        raise HTTPException(401, "Not connected to SmugMug")
    return SmugMugClient(API_KEY, API_SECRET, row["access_token"], row["access_token_secret"]), row["smugmug_user"]


@router.get("/folders")
def list_folders(path: str = Query(default="")):
    """
    Return subfolders + albums at `path`.
    path="" → root level.
    path="2026" → contents of the 2026 folder.
    """
    client, user = _client()

    folders = client.get_folders(user, path)
    albums = client.get_folder_albums(user, path)

    return {
        "path": path,
        "folders": [
            {
                "name": f.get("Name", ""),
                "path": _rel_path(f.get("UrlPath", ""), user),
            }
            for f in folders
        ],
        "albums": [
            {
                "name": a.get("Name", ""),
                "key": a.get("AlbumKey", ""),
                "image_count": a.get("ImageCount", 0),
            }
            for a in albums
        ],
    }


def _rel_path(url_path: str, user_nick: str) -> str:
    """Extract relative folder path from a SmugMug UrlPath."""
    # UrlPath looks like /user/nick/2026/Summer → we want 2026/Summer
    prefix = f"/user/{user_nick}/"
    if url_path.startswith(prefix):
        return url_path[len(prefix):]
    return url_path.lstrip("/")

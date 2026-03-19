from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.indexer import start_indexing_job, get_active_job
from services.clusterer import run_clustering
from typing import Optional
import asyncio

router = APIRouter(prefix="/index")


class IndexScope(BaseModel):
    folder_path: Optional[str] = None   # e.g. "2026" or "2026/Summer"
    album_keys: Optional[list[str]] = None  # specific album keys


@router.post("/start")
async def start_index(scope: IndexScope = IndexScope()):
    job = get_active_job()
    if job and job["status"] == "running":
        raise HTTPException(409, "Indexing already running")
    job_id = start_indexing_job(
        folder_path=scope.folder_path,
        album_keys=scope.album_keys,
    )
    return {"job_id": job_id, "status": "started"}

@router.get("/status")
def index_status():
    job = get_active_job()
    if not job:
        return {"status": "idle", "indexed": 0, "total": 0}
    return {
        "status": job["status"],
        "indexed": job["indexed_count"],
        "total": job["total_images"],
        "last_image_key": job["last_image_key"],
        "error": job["error"],
    }

@router.post("/cluster")
async def cluster():
    result = await asyncio.to_thread(run_clustering)
    return result

from fastapi import APIRouter, HTTPException
from services.indexer import start_indexing_job, get_active_job
from services.clusterer import run_clustering
import asyncio

router = APIRouter(prefix="/index")

@router.post("/start")
async def start_index():
    job = get_active_job()
    if job and job["status"] == "running":
        raise HTTPException(409, "Indexing already running")
    job_id = start_indexing_job()
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

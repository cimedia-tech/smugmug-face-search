import base64
from fastapi import APIRouter, HTTPException
from db import get_conn

router = APIRouter(prefix="/people")

@router.get("")
def list_people():
    with get_conn() as conn:
        clusters = conn.execute("""
            SELECT pc.id, pc.name, pc.sample_face_id,
                   COUNT(fi.id) as photo_count,
                   fi.face_crop
            FROM person_clusters pc
            LEFT JOIN face_index fi ON fi.cluster_id = pc.id
            LEFT JOIN face_index sample ON sample.id = pc.sample_face_id
            GROUP BY pc.id
            ORDER BY photo_count DESC
        """).fetchall()
    result = []
    for c in clusters:
        crop_b64 = None
        if c["face_crop"]:
            crop_b64 = base64.b64encode(c["face_crop"]).decode()
        result.append({
            "id": c["id"],
            "name": c["name"] or f"Unknown #{c['id']}",
            "photo_count": c["photo_count"],
            "sample_face_b64": crop_b64,
        })
    return result

@router.post("/{cluster_id}/tag")
def tag_person(cluster_id: int, body: dict):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(400, "name required")
    with get_conn() as conn:
        conn.execute("UPDATE person_clusters SET name=? WHERE id=?", (name, cluster_id))
    return {"ok": True}

@router.get("/{cluster_id}/photos")
def person_photos(cluster_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT smugmug_image_key, thumbnail_url, image_url
            FROM face_index WHERE cluster_id=?
        """, (cluster_id,)).fetchall()
    return [dict(r) for r in rows]

@router.get("/photo/{image_key}/faces")
def photo_faces(image_key: str):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT fi.id, fi.face_index_in_photo,
                   fi.bbox_x, fi.bbox_y, fi.bbox_w, fi.bbox_h,
                   fi.cluster_id, pc.name, fi.face_crop
            FROM face_index fi
            LEFT JOIN person_clusters pc ON pc.id = fi.cluster_id
            WHERE fi.smugmug_image_key=?
        """, (image_key,)).fetchall()
    result = []
    for r in rows:
        crop_b64 = base64.b64encode(r["face_crop"]).decode() if r["face_crop"] else None
        result.append({
            "face_id": r["id"],
            "face_index": r["face_index_in_photo"],
            "bbox": {"x": r["bbox_x"], "y": r["bbox_y"], "w": r["bbox_w"], "h": r["bbox_h"]},
            "cluster_id": r["cluster_id"],
            "name": r["name"] or (f"Unknown #{r['cluster_id']}" if r["cluster_id"] else "Unmatched"),
            "crop_b64": crop_b64,
        })
    return result

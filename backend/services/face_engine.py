import io
import os
import numpy as np
from PIL import Image

_models_loaded = False

DETECTOR = os.environ.get("FACE_DETECTOR", "yunet")
MAX_DIM = int(os.environ.get("FACE_MAX_DIM", "960"))   # reduced from 1280
MIN_FACE_PX = int(os.environ.get("FACE_MIN_PX", "30")) # skip tiny faces

# Image extensions worth processing
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}


def is_processable_url(url: str) -> bool:
    """Skip videos, raw files, and other non-image formats."""
    ext = os.path.splitext(url.split("?")[0].lower())[1]
    return ext in IMAGE_EXTS or ext == ""  # empty ext = SmugMug sized URL, always process


def preload_models():
    """Call once per process to warm up the model before processing starts."""
    global _models_loaded
    if _models_loaded:
        return
    try:
        from deepface import DeepFace
        blank = np.zeros((160, 160, 3), dtype=np.uint8)
        DeepFace.represent(blank, model_name="Facenet512", enforce_detection=False,
                           detector_backend=DETECTOR)
        _models_loaded = True
        print(f"DeepFace ready (detector={DETECTOR}, max_dim={MAX_DIM}, pid={os.getpid()})")
    except Exception as e:
        print(f"Model preload warning: {e}")


def extract_faces(img_bytes: bytes) -> list[dict]:
    """
    CPU-bound. Safe to run in a worker process.
    Returns list of { embedding, bbox, crop_bytes }.
    """
    from deepface import DeepFace

    # Ensure model is loaded in this process
    if not _models_loaded:
        preload_models()

    img_array = _bytes_to_array(img_bytes)
    orig_h, orig_w = img_array.shape[:2]

    # Resize large images — faces detectable at 960px
    if max(orig_h, orig_w) > MAX_DIM:
        scale = MAX_DIM / max(orig_h, orig_w)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        img_array = np.array(Image.fromarray(img_array).resize((new_w, new_h)))

    h, w = img_array.shape[:2]

    try:
        results = DeepFace.represent(
            img_array,
            model_name="Facenet512",
            enforce_detection=True,
            detector_backend=DETECTOR,
        )
    except ValueError:
        return []

    faces = []
    for r in results:
        region = r.get("facial_area", {})
        x, y, fw, fh = (region.get(k, 0) for k in ["x", "y", "w", "h"])

        # Skip faces that are too small to produce useful embeddings
        if fw < MIN_FACE_PX or fh < MIN_FACE_PX:
            continue

        emb = np.array(r["embedding"], dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        bbox = {"x": x/w, "y": y/h, "w": fw/w, "h": fh/h}

        crop = img_array[max(0, y):y+fh, max(0, x):x+fw]
        pil_crop = Image.fromarray(crop).resize((96, 96))
        buf = io.BytesIO()
        pil_crop.save(buf, format="JPEG", quality=80)

        faces.append({"embedding": emb, "bbox": bbox, "crop_bytes": buf.getvalue()})

    return faces


def _bytes_to_array(img_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)


def embedding_from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()


def embedding_to_blob(emb: np.ndarray) -> bytes:
    return emb.astype(np.float32).tobytes()

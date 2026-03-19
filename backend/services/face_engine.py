import io
import numpy as np
from PIL import Image

_models_loaded = False

def preload_models():
    global _models_loaded
    if _models_loaded:
        return
    try:
        from deepface import DeepFace
        # Trigger model download by running on a tiny blank image
        blank = np.zeros((160, 160, 3), dtype=np.uint8)
        DeepFace.represent(blank, model_name="Facenet512", enforce_detection=False)
        _models_loaded = True
        print("DeepFace models loaded.")
    except Exception as e:
        print(f"Model preload warning: {e}")

def extract_faces(img_bytes: bytes) -> list[dict]:
    """
    Returns list of dicts:
      { embedding: np.ndarray(512,), bbox: {x,y,w,h} normalized, crop_bytes: bytes }
    """
    from deepface import DeepFace
    import numpy as np

    img_array = _bytes_to_array(img_bytes)
    h, w = img_array.shape[:2]

    try:
        results = DeepFace.represent(
            img_array,
            model_name="Facenet512",
            enforce_detection=True,
            detector_backend="retinaface",
        )
    except ValueError:
        # No faces detected
        return []

    faces = []
    for r in results:
        emb = np.array(r["embedding"], dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm  # L2 normalize for cosine via dot product

        region = r.get("facial_area", {})
        x, y, fw, fh = (region.get(k, 0) for k in ["x", "y", "w", "h"])
        bbox = {"x": x/w, "y": y/h, "w": fw/w, "h": fh/h}

        # Crop face for thumbnail
        crop = img_array[max(0,y):y+fh, max(0,x):x+fw]
        pil_crop = Image.fromarray(crop).resize((96, 96))
        buf = io.BytesIO()
        pil_crop.save(buf, format="JPEG", quality=80)
        crop_bytes = buf.getvalue()

        faces.append({"embedding": emb, "bbox": bbox, "crop_bytes": crop_bytes})

    return faces

def _bytes_to_array(img_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)

def embedding_from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()

def embedding_to_blob(emb: np.ndarray) -> bytes:
    return emb.astype(np.float32).tobytes()

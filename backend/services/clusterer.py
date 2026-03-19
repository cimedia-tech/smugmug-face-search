import numpy as np
from sklearn.cluster import DBSCAN
from db import get_conn
from services.face_engine import embedding_from_blob

EPS = 0.35          # cosine distance threshold (tunable)
MIN_SAMPLES = 2     # min faces to form a cluster

def run_clustering():
    """Cluster all face embeddings. Preserves existing name tags by matching centroids."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, face_embedding, cluster_id FROM face_index"
        ).fetchall()

    if not rows:
        return {"clusters": 0, "noise": 0}

    ids = [r["id"] for r in rows]
    embeddings = np.array([embedding_from_blob(r["face_embedding"]) for r in rows])

    # Normalize for cosine distance
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    db = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES, metric="cosine", n_jobs=-1)
    labels = db.fit_predict(embeddings)

    # Preserve existing cluster names: map new label -> existing cluster_id if centroid matches
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, name, sample_face_id FROM person_clusters"
        ).fetchall()
        old_face_clusters = {r["id"]: r["cluster_id"] for r in
                             conn.execute("SELECT id, cluster_id FROM face_index").fetchall()}

    # Build centroid for each new cluster label
    unique_labels = set(labels) - {-1}
    new_centroids = {}
    for lbl in unique_labels:
        mask = labels == lbl
        new_centroids[lbl] = embeddings[mask].mean(axis=0)

    # Match new labels to existing cluster_ids by min cosine distance
    label_to_cluster_id = {}
    if existing:
        ex_ids = [e["id"] for e in existing]
        ex_face_ids = [e["sample_face_id"] for e in existing]
        # Get embeddings for sample faces
        with get_conn() as conn:
            ex_embs = []
            for fid in ex_face_ids:
                row = conn.execute("SELECT face_embedding FROM face_index WHERE id=?", (fid,)).fetchone()
                if row:
                    ex_embs.append(embedding_from_blob(row["face_embedding"]))
                else:
                    ex_embs.append(None)

        for lbl, centroid in new_centroids.items():
            best_dist = EPS
            best_id = None
            for eid, eemb in zip(ex_ids, ex_embs):
                if eemb is None:
                    continue
                dist = 1 - float(np.dot(centroid, eemb))
                if dist < best_dist:
                    best_dist = dist
                    best_id = eid
            if best_id:
                label_to_cluster_id[lbl] = best_id

    # Create new clusters for unmatched labels
    with get_conn() as conn:
        for lbl in unique_labels:
            if lbl not in label_to_cluster_id:
                # Pick sample face (face closest to centroid)
                mask = np.where(labels == lbl)[0]
                centroid = new_centroids[lbl]
                dists = [1 - float(np.dot(embeddings[i], centroid)) for i in mask]
                sample_face_id = ids[mask[int(np.argmin(dists))]]
                cur = conn.execute(
                    "INSERT INTO person_clusters(sample_face_id) VALUES(?)",
                    (sample_face_id,)
                )
                label_to_cluster_id[lbl] = cur.lastrowid

        # Update face_index cluster assignments
        for i, (face_id, lbl) in enumerate(zip(ids, labels)):
            cluster_id = label_to_cluster_id.get(lbl)  # None for noise (-1)
            conn.execute(
                "UPDATE face_index SET cluster_id=? WHERE id=?",
                (cluster_id, face_id)
            )

    n_clusters = len(unique_labels)
    n_noise = int(np.sum(labels == -1))
    return {"clusters": n_clusters, "noise": n_noise}

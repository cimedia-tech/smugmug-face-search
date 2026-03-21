#!/usr/bin/env python3
"""
SmugMug Face Search — local clustering CLI

Reads all face embeddings from Supabase, runs DBSCAN clustering,
preserves existing person names by matching centroids, then writes
cluster assignments back to Supabase.

Usage:
  cd cli
  python cluster.py
"""
import json
import os
import sys

import numpy as np
from dotenv import load_dotenv
from sklearn.cluster import DBSCAN
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

EPS         = 0.35   # cosine distance threshold
MIN_SAMPLES = 2      # minimum faces to form a cluster


def sb():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_embedding(val) -> np.ndarray | None:
    """pgvector returns embeddings as a list or JSON string."""
    if val is None:
        return None
    if isinstance(val, list):
        return np.array(val, dtype=np.float32)
    if isinstance(val, str):
        return np.array(json.loads(val), dtype=np.float32)
    return None


def main():
    client = sb()

    print("Loading face embeddings from Supabase...")
    r = client.table('face_index').select('id, face_embedding, cluster_id').execute()
    all_rows = r.data or []

    # Filter out sentinel rows (no-face images) and rows with null embeddings
    rows = [row for row in all_rows
            if row.get('face_embedding') is not None
            and row.get('face_index_in_photo', 0) != -1]

    if not rows:
        print("No face embeddings found. Index some photos first.")
        return

    print(f"Loaded {len(rows)} face embeddings")

    ids        = [r['id'] for r in rows]
    embeddings = np.array([parse_embedding(r['face_embedding']) for r in rows], dtype=np.float32)

    # Normalize for cosine distance
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    print("Running DBSCAN clustering...")
    db     = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES, metric='cosine', n_jobs=-1)
    labels = db.fit_predict(embeddings)

    unique_labels = set(labels) - {-1}
    print(f"Found {len(unique_labels)} clusters, {int(np.sum(labels == -1))} noise points")

    # Build centroids for each new cluster label
    new_centroids = {}
    for lbl in unique_labels:
        mask = labels == lbl
        new_centroids[lbl] = embeddings[mask].mean(axis=0)

    # Load existing clusters to preserve names
    ex_r = client.table('person_clusters').select('id, name, sample_face_id').execute()
    existing = ex_r.data or []

    # Match new labels to existing cluster IDs via centroid cosine similarity
    label_to_cluster_id: dict[int, int] = {}

    if existing:
        ex_ids      = [e['id'] for e in existing]
        ex_face_ids = [e['sample_face_id'] for e in existing]

        # Fetch sample face embeddings
        ex_embs = []
        for fid in ex_face_ids:
            if fid is None:
                ex_embs.append(None)
                continue
            fe_r = client.table('face_index').select('face_embedding').eq('id', fid).single().execute()
            emb  = parse_embedding(fe_r.data['face_embedding']) if fe_r.data else None
            if emb is not None:
                norm = np.linalg.norm(emb)
                emb  = emb / norm if norm > 0 else emb
            ex_embs.append(emb)

        for lbl, centroid in new_centroids.items():
            best_dist, best_id = EPS, None
            for eid, eemb in zip(ex_ids, ex_embs):
                if eemb is None:
                    continue
                dist = 1.0 - float(np.dot(centroid, eemb))
                if dist < best_dist:
                    best_dist, best_id = dist, eid
            if best_id:
                label_to_cluster_id[lbl] = best_id

    # Create new clusters for unmatched labels
    for lbl in unique_labels:
        if lbl in label_to_cluster_id:
            continue
        mask     = np.where(labels == lbl)[0]
        centroid = new_centroids[lbl]
        dists    = [1.0 - float(np.dot(embeddings[i], centroid)) for i in mask]
        sample_face_id = ids[mask[int(np.argmin(dists))]]
        new_r = client.table('person_clusters').insert({'sample_face_id': sample_face_id}).execute()
        label_to_cluster_id[lbl] = new_r.data[0]['id']

    # Write cluster assignments back in batches
    print("Writing cluster assignments...")
    BATCH = 500
    updates = [
        {'id': face_id, 'cluster_id': label_to_cluster_id.get(int(lbl))}
        for face_id, lbl in zip(ids, labels)
    ]
    for i in range(0, len(updates), BATCH):
        batch = updates[i:i + BATCH]
        client.table('face_index').upsert(batch).execute()
        print(f"  {min(i + BATCH, len(updates))}/{len(updates)}")

    print(f"\nDone — {len(unique_labels)} clusters, {int(np.sum(labels == -1))} unassigned faces")


if __name__ == '__main__':
    main()

# SmugMug Face Search

Browse your SmugMug photos by person — like Google Photos, but for SmugMug.

---

## What Was Built

A full-stack web app that indexes your SmugMug gallery, clusters faces by identity, lets you tag people by name, then browse all their photos instantly.

### How It Works

1. **Connect** your SmugMug account via OAuth
2. **Pick a scope** — entire account, a specific folder (e.g. "2026"), or individual albums
3. **Index** — backend downloads each photo, runs face detection (DeepFace/Facenet512), stores a 512-dim embedding + bounding box + face crop thumbnail per face in SQLite
4. **Cluster** — DBSCAN groups faces by identity; stable across re-runs (existing name tags are preserved by centroid matching)
5. **Tag** — give each person a name ("Dad", "Sarah", etc.)
6. **Browse** — grid of people → click a person → see every photo they appear in → click a photo → see bounding boxes drawn over each face

### Audio Alert
When a long indexing job finishes (can take hours for 10k+ photos), the browser plays an audible tone and fires a desktop notification so you know to come back.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 + Tailwind CSS + TypeScript |
| Backend | FastAPI (Python) |
| Face Recognition | DeepFace — Facenet512 model |
| Clustering | DBSCAN (scikit-learn), cosine distance |
| Storage | SQLite (WAL mode) |
| SmugMug Auth | OAuth 1.0a |

---

## Running Locally

### Prerequisites
- Python 3.10+
- Node.js 18+ (tested on v24 via pnpm)
- SmugMug API key + secret from https://www.smugmug.com/app/account/keys

### Backend
```bash
cd backend
pip install -r requirements.txt
pip install tf-keras   # required for TF 2.21+

SMUGMUG_API_KEY=your_key \
SMUGMUG_API_SECRET=your_secret \
CALLBACK_URL=http://localhost:8001/auth/callback \
FRONTEND_URL=http://localhost:3000 \
uvicorn main:app --port 8001
```

### Frontend
```bash
cd frontend
pnpm install   # use pnpm, not npm (npm has extraction issues on Windows)
BACKEND_URL=http://localhost:8001 pnpm dev
```

Visit http://localhost:3000

---

## Project Structure

```
smugmug-face-search/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, lifespan startup
│   ├── db.py                    # SQLite schema (WAL mode)
│   ├── routes/
│   │   ├── auth.py              # OAuth 1.0a flow
│   │   ├── browse.py            # Folder/album tree browser
│   │   ├── index.py             # Indexing job control
│   │   └── people.py           # People, tagging, photo lookup
│   └── services/
│       ├── smugmug.py           # SmugMug API client (rate-limited)
│       ├── face_engine.py       # DeepFace wrapper, L2-normalised embeddings
│       ├── indexer.py           # Background indexing job
│       └── clusterer.py        # DBSCAN clustering with stable ID matching
└── frontend/
    ├── app/
    │   ├── page.tsx             # Home: connect + index status
    │   ├── people/page.tsx      # People grid
    │   ├── people/[id]/page.tsx # Person detail + name editor
    │   └── gallery/[key]/page.tsx # Photo with face bounding boxes
    └── components/
        ├── IndexStatus.tsx      # Progress bar, scope picker, audio alert
        ├── PersonCard.tsx       # Face thumbnail card
        ├── PhotoGrid.tsx        # Responsive photo grid
        └── FaceOverlay.tsx      # Canvas bounding box overlay
```

---

## Deployment

- **Frontend** — deployed to Vercel: https://frontend-five-pi-24op1dne7k.vercel.app
- **Backend** — runs locally (requires Python + ~2GB RAM for DeepFace). Not on free cloud hosting — DeepFace needs 1.5–2GB RAM which free tiers don't provide. Cheapest cloud option: Render Starter ($7/mo) or Railway (~$5/mo).
- **GitHub** — https://github.com/cimedia-tech/smugmug-face-search

---

## Known Notes

- First backend startup downloads Facenet512 model weights (~90MB) — takes ~30s
- Indexing 10k photos takes 3–14 hours depending on hardware and photo sizes
- Use `pnpm` on Windows — npm has file extraction issues with Next.js on Windows
- SmugMug OAuth callback URL must match exactly what's registered in your API key settings

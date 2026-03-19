import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from db import init_db
from services.face_engine import preload_models
from routes.auth import router as auth_router
from routes.browse import router as browse_router
from routes.index import router as index_router
from routes.people import router as people_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    preload_models()
    yield

app = FastAPI(title="SmugMug Face Search", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(browse_router)
app.include_router(index_router)
app.include_router(people_router)

@app.get("/health")
def health():
    return {"ok": True}

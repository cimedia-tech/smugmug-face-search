import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from services.smugmug import get_request_token, get_authorize_url, get_access_token, SmugMugClient
from db import get_conn

router = APIRouter(prefix="/auth")

API_KEY = os.environ.get("SMUGMUG_API_KEY", "")
API_SECRET = os.environ.get("SMUGMUG_API_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
CALLBACK_URL = os.environ.get("CALLBACK_URL", "http://localhost:8000/auth/callback")

# Temp store for request tokens (in-process, fine for single-user)
_pending: dict[str, str] = {}

@router.get("/start")
def auth_start():
    if not API_KEY:
        raise HTTPException(500, "SMUGMUG_API_KEY not configured")
    token, secret = get_request_token(API_KEY, API_SECRET, CALLBACK_URL)
    _pending[token] = secret
    url = get_authorize_url(API_KEY, token)
    return RedirectResponse(url)

@router.get("/callback")
def auth_callback(oauth_token: str, oauth_verifier: str):
    secret = _pending.pop(oauth_token, None)
    if not secret:
        raise HTTPException(400, "Unknown oauth_token")
    access_token, access_secret = get_access_token(
        API_KEY, API_SECRET, oauth_token, secret, oauth_verifier
    )
    client = SmugMugClient(API_KEY, API_SECRET, access_token, access_secret)
    user = client.get_user()
    nick = user.get("NickName", "")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO oauth_tokens(id, access_token, access_token_secret, smugmug_user)
            VALUES(1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                access_token=excluded.access_token,
                access_token_secret=excluded.access_token_secret,
                smugmug_user=excluded.smugmug_user,
                saved_at=CURRENT_TIMESTAMP
        """, (access_token, access_secret, nick))

    return RedirectResponse(f"{FRONTEND_URL}/?connected=true")

@router.get("/status")
def auth_status():
    with get_conn() as conn:
        row = conn.execute("SELECT smugmug_user, saved_at FROM oauth_tokens WHERE id=1").fetchone()
    if not row:
        return {"connected": False}
    return {"connected": True, "user": row["smugmug_user"], "since": row["saved_at"]}

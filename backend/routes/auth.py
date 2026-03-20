import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from services.smugmug import get_request_token, get_authorize_url, get_access_token, SmugMugClient
from db import get_conn

router = APIRouter(prefix="/auth")

def _cfg():
    return {
        "key": os.environ.get("SMUGMUG_API_KEY", ""),
        "secret": os.environ.get("SMUGMUG_API_SECRET", ""),
        "frontend": os.environ.get("FRONTEND_URL", "http://localhost:3000"),
        "callback": os.environ.get("CALLBACK_URL", "http://localhost:8001/auth/callback"),
    }

# Temp store for request tokens (in-process, fine for single-user)
_pending: dict[str, str] = {}

@router.get("/start")
def auth_start():
    cfg = _cfg()
    if not cfg["key"]:
        raise HTTPException(500, "SMUGMUG_API_KEY not configured")
    token, secret = get_request_token(cfg["key"], cfg["secret"], cfg["callback"])
    _pending[token] = secret
    url = get_authorize_url(cfg["key"], token)
    return RedirectResponse(url)

@router.get("/callback")
def auth_callback(oauth_token: str, oauth_verifier: str):
    cfg = _cfg()
    secret = _pending.pop(oauth_token, None)
    if not secret:
        raise HTTPException(400, "Unknown oauth_token")
    access_token, access_secret = get_access_token(
        cfg["key"], cfg["secret"], oauth_token, secret, oauth_verifier
    )
    client = SmugMugClient(cfg["key"], cfg["secret"], access_token, access_secret)
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

    return RedirectResponse(f"{cfg['frontend']}/?connected=true")

@router.get("/status")
def auth_status():
    with get_conn() as conn:
        row = conn.execute("SELECT smugmug_user, saved_at FROM oauth_tokens WHERE id=1").fetchone()
    if not row:
        return {"connected": False}
    return {"connected": True, "user": row["smugmug_user"], "since": row["saved_at"]}

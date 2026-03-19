import time
import requests
from requests_oauthlib import OAuth1Session

SMUGMUG_BASE = "https://api.smugmug.com"
REQUEST_TOKEN_URL = "https://api.smugmug.com/services/oauth/1.0a/getRequestToken"
AUTHORIZE_URL = "https://api.smugmug.com/services/oauth/1.0a/authorize"
ACCESS_TOKEN_URL = "https://api.smugmug.com/services/oauth/1.0a/getAccessToken"

_RATE_DELAY = 0.2  # 5 req/sec max

def get_request_token(api_key: str, api_secret: str, callback_url: str):
    oauth = OAuth1Session(api_key, client_secret=api_secret, callback_uri=callback_url)
    r = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    return r["oauth_token"], r["oauth_token_secret"]

def get_authorize_url(api_key: str, request_token: str) -> str:
    return f"{AUTHORIZE_URL}?oauth_token={request_token}&Access=Full&Permissions=Read"

def get_access_token(api_key: str, api_secret: str, request_token: str,
                     request_token_secret: str, verifier: str):
    oauth = OAuth1Session(
        api_key, client_secret=api_secret,
        resource_owner_key=request_token,
        resource_owner_secret=request_token_secret,
        verifier=verifier,
    )
    r = oauth.fetch_access_token(ACCESS_TOKEN_URL)
    return r["oauth_token"], r["oauth_token_secret"]

class SmugMugClient:
    def __init__(self, api_key: str, api_secret: str, token: str, token_secret: str):
        self.session = OAuth1Session(
            api_key, client_secret=api_secret,
            resource_owner_key=token,
            resource_owner_secret=token_secret,
        )

    def _get(self, path: str, params: dict = None):
        url = SMUGMUG_BASE + path
        p = {"_accept": "application/json", **(params or {})}
        time.sleep(_RATE_DELAY)
        r = self.session.get(url, params=p)
        r.raise_for_status()
        return r.json()["Response"]

    def get_user(self):
        data = self._get("/api/v2!authuser")
        return data["User"]

    def get_albums(self, user_nick: str):
        albums = []
        start = 1
        while True:
            data = self._get(f"/api/v2/user/{user_nick}!albums",
                             {"start": start, "count": 100})
            albums.extend(data.get("Album", []))
            pages = data.get("Pages", {})
            if pages.get("NextPage"):
                start += 100
            else:
                break
        return albums

    def get_images(self, album_key: str):
        images = []
        start = 1
        while True:
            data = self._get(f"/api/v2/album/{album_key}!images",
                             {"start": start, "count": 100})
            images.extend(data.get("AlbumImage", []))
            pages = data.get("Pages", {})
            if pages.get("NextPage"):
                start += 100
            else:
                break
        return images

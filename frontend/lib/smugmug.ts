/**
 * SmugMug OAuth 1.0a client — TypeScript port of backend/services/smugmug.py
 * Uses Node.js built-in crypto (no extra dependencies needed).
 */
import crypto from 'crypto'

const SMUGMUG_BASE      = 'https://api.smugmug.com'
const REQUEST_TOKEN_URL = `${SMUGMUG_BASE}/services/oauth/1.0a/getRequestToken`
const AUTHORIZE_URL     = `${SMUGMUG_BASE}/services/oauth/1.0a/authorize`
const ACCESS_TOKEN_URL  = `${SMUGMUG_BASE}/services/oauth/1.0a/getAccessToken`
const RATE_DELAY_MS     = 200

// ── OAuth 1.0a helpers ──────────────────────────────────────────────────────

function pct(s: string): string {
  return encodeURIComponent(s).replace(/[!'()*]/g, c => '%' + c.charCodeAt(0).toString(16).toUpperCase())
}

function sign(
  method: string,
  url: string,
  params: Record<string, string>,
  consumerSecret: string,
  tokenSecret = ''
): string {
  const normalized = Object.entries(params)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${pct(k)}=${pct(v)}`)
    .join('&')
  const base = `${method.toUpperCase()}&${pct(url)}&${pct(normalized)}`
  const key  = `${pct(consumerSecret)}&${pct(tokenSecret)}`
  return crypto.createHmac('sha1', key).update(base).digest('base64')
}

function oauthHeader(params: Record<string, string>): string {
  const parts = Object.entries(params)
    .filter(([k]) => k.startsWith('oauth_'))
    .map(([k, v]) => `${k}="${pct(v)}"`)
  return 'OAuth realm="", ' + parts.join(', ')
}

function baseParams(consumerKey: string, tokenKey = ''): Record<string, string> {
  const p: Record<string, string> = {
    oauth_consumer_key:     consumerKey,
    oauth_nonce:            crypto.randomBytes(16).toString('hex'),
    oauth_signature_method: 'HMAC-SHA1',
    oauth_timestamp:        Math.floor(Date.now() / 1000).toString(),
    oauth_version:          '1.0',
  }
  if (tokenKey) p.oauth_token = tokenKey
  return p
}

async function oauthPost(url: string, params: Record<string, string>): Promise<URLSearchParams> {
  const r = await fetch(url, {
    method: 'POST',
    headers: { Authorization: oauthHeader(params) },
  })
  if (!r.ok) throw new Error(`OAuth POST ${url} → ${r.status}: ${await r.text()}`)
  return new URLSearchParams(await r.text())
}

// ── Public auth functions ───────────────────────────────────────────────────

export async function getRequestToken(apiKey: string, apiSecret: string, callbackUrl: string) {
  const params: Record<string, string> = { ...baseParams(apiKey), oauth_callback: callbackUrl }
  params.oauth_signature = sign('POST', REQUEST_TOKEN_URL, params, apiSecret)
  const result = await oauthPost(REQUEST_TOKEN_URL, params)
  return {
    token:  result.get('oauth_token')!,
    secret: result.get('oauth_token_secret')!,
  }
}

export function getAuthorizeUrl(requestToken: string): string {
  return `${AUTHORIZE_URL}?oauth_token=${requestToken}&Access=Full&Permissions=Read`
}

export async function getAccessToken(
  apiKey: string,
  apiSecret: string,
  requestToken: string,
  requestSecret: string,
  verifier: string
) {
  const params: Record<string, string> = { ...baseParams(apiKey, requestToken), oauth_verifier: verifier }
  params.oauth_signature = sign('POST', ACCESS_TOKEN_URL, params, apiSecret, requestSecret)
  const result = await oauthPost(ACCESS_TOKEN_URL, params)
  return {
    token:  result.get('oauth_token')!,
    secret: result.get('oauth_token_secret')!,
  }
}

// ── SmugMug API client ──────────────────────────────────────────────────────

export class SmugMugClient {
  constructor(
    private apiKey: string,
    private apiSecret: string,
    private token: string,
    private tokenSecret: string
  ) {}

  async get(path: string, extraParams: Record<string, string> = {}): Promise<any> {
    await new Promise(r => setTimeout(r, RATE_DELAY_MS))
    const url     = SMUGMUG_BASE + path
    const qParams = { _accept: 'application/json', ...extraParams }
    const all: Record<string, string> = { ...baseParams(this.apiKey, this.token), ...qParams }
    all.oauth_signature = sign('GET', url, all, this.apiSecret, this.tokenSecret)
    const r = await fetch(`${url}?${new URLSearchParams(qParams)}`, {
      headers: { Authorization: oauthHeader(all) },
    })
    if (!r.ok) throw new Error(`SmugMug ${r.status}: ${path}`)
    return (await r.json()).Response
  }

  async getUser() {
    return (await this.get('/api/v2!authuser')).User
  }

  async getFolders(userNick: string, folderPath = ''): Promise<any[]> {
    let path = `/api/v2/folder/user/${userNick}`
    if (folderPath) path += `/${folderPath.replace(/^\//, '')}`
    try { return (await this.get(path + '!folders')).Folder ?? [] } catch { return [] }
  }

  async getFolderAlbums(userNick: string, folderPath = ''): Promise<any[]> {
    let path = `/api/v2/folder/user/${userNick}`
    if (folderPath) path += `/${folderPath.replace(/^\//, '')}`
    try { return (await this.get(path + '!albums')).Album ?? [] } catch { return [] }
  }

  async getAlbums(userNick: string): Promise<any[]> {
    const albums: any[] = []
    let start = 1
    while (true) {
      const data = await this.get(`/api/v2/user/${userNick}!albums`, { start: String(start), count: '100' })
      albums.push(...(data.Album ?? []))
      if (!data.Pages?.NextPage) break
      start += 100
    }
    return albums
  }

  async getImages(albumKey: string): Promise<any[]> {
    const images: any[] = []
    let start = 1
    while (true) {
      try {
        const data = await this.get(`/api/v2/album/${albumKey}!images`, { start: String(start), count: '100' })
        images.push(...(data.AlbumImage ?? []))
        if (!data.Pages?.NextPage) break
        start += 100
      } catch (e) {
        console.warn(`Skipping album ${albumKey}: ${e}`)
        break
      }
    }
    return images
  }
}

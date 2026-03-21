import { NextRequest, NextResponse } from 'next/server'
import { getAccessToken, SmugMugClient } from '@/lib/smugmug'
import { serverClient } from '@/lib/supabase'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const oauthToken    = searchParams.get('oauth_token')
  const oauthVerifier = searchParams.get('oauth_verifier')

  if (!oauthToken || !oauthVerifier) {
    return NextResponse.json({ error: 'Missing OAuth params' }, { status: 400 })
  }

  const sb = serverClient()

  // Retrieve and delete the pending request token secret
  const { data: pending, error: lookupError } = await sb
    .from('oauth_pending')
    .select('request_token_secret')
    .eq('request_token', oauthToken)
    .single()

  if (!pending) {
    console.error('oauth_pending lookup failed:', lookupError?.message, '| token:', oauthToken)
    return NextResponse.json({
      error: 'Unknown oauth_token — try connecting again',
      detail: lookupError?.message,
      token: oauthToken,
    }, { status: 400 })
  }

  await sb.from('oauth_pending').delete().eq('request_token', oauthToken)

  // Exchange for access token
  const { token, secret } = await getAccessToken(
    process.env.SMUGMUG_API_KEY!,
    process.env.SMUGMUG_API_SECRET!,
    oauthToken,
    pending.request_token_secret,
    oauthVerifier
  )

  // Fetch the user's nickname
  const client = new SmugMugClient(
    process.env.SMUGMUG_API_KEY!,
    process.env.SMUGMUG_API_SECRET!,
    token,
    secret
  )
  const user = await client.getUser()
  const nick = user?.NickName ?? ''

  // Store tokens (upsert so re-connecting overwrites)
  await sb.from('oauth_tokens').upsert({
    id:                  1,
    access_token:        token,
    access_token_secret: secret,
    smugmug_user:        nick,
  })

  const frontendUrl = process.env.FRONTEND_URL ?? 'http://localhost:3000'
  return NextResponse.redirect(`${frontendUrl}/?connected=true`)
}

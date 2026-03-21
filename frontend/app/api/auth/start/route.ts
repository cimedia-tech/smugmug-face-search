import { NextResponse } from 'next/server'
import { getRequestToken, getAuthorizeUrl } from '@/lib/smugmug'
import { serverClient } from '@/lib/supabase'

export async function GET() {
  const apiKey    = process.env.SMUGMUG_API_KEY!
  const apiSecret = process.env.SMUGMUG_API_SECRET!
  const callback  = process.env.CALLBACK_URL!

  if (!apiKey) return NextResponse.json({ error: 'SMUGMUG_API_KEY not configured' }, { status: 500 })

  const { token, secret } = await getRequestToken(apiKey, apiSecret, callback)

  const { error } = await serverClient()
    .from('oauth_pending')
    .upsert({ request_token: token, request_token_secret: secret })

  if (error) {
    console.error('oauth_pending upsert failed:', error)
    return NextResponse.json({ error: 'Failed to store OAuth token', detail: error.message }, { status: 500 })
  }

  return NextResponse.redirect(getAuthorizeUrl(token))
}

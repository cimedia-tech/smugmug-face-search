import { NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function GET() {
  const { data } = await serverClient()
    .from('oauth_tokens')
    .select('smugmug_user, saved_at')
    .eq('id', 1)
    .single()

  if (!data) return NextResponse.json({ connected: false })
  return NextResponse.json({ connected: true, user: data.smugmug_user, since: data.saved_at })
}

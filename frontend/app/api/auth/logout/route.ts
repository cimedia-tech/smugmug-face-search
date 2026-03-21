import { NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function POST() {
  await serverClient().from('oauth_tokens').delete().eq('id', 1)
  return NextResponse.json({ ok: true })
}

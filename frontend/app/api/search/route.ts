import { NextRequest, NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function POST(req: NextRequest) {
  const sb = serverClient()
  const body = await req.json().catch(() => ({}))

  const image_url = body.image_url as string | undefined
  if (!image_url) {
    return NextResponse.json({ error: 'image_url required' }, { status: 400 })
  }

  const { data, error } = await sb
    .from('search_jobs')
    .insert({ image_url, status: 'pending', top_k: 30 })
    .select('id')
    .single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ id: data.id })
}

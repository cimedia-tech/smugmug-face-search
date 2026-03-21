import { NextRequest, NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function POST(req: NextRequest) {
  const sb = serverClient()

  // Reject if a job is already running
  const { data: existing } = await sb
    .from('indexing_jobs')
    .select('status')
    .order('id', { ascending: false })
    .limit(1)
    .single()

  if (existing?.status === 'running') {
    return NextResponse.json({ error: 'Indexing already running' }, { status: 409 })
  }

  const body = await req.json().catch(() => ({}))

  const { data, error } = await sb
    .from('indexing_jobs')
    .insert({
      status:      'pending',
      folder_path: body.folder_path ?? null,
      album_keys:  body.album_keys  ?? null,
    })
    .select('id')
    .single()

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({
    job_id:  data.id,
    status:  'started',
    message: 'Job queued. Run: python cli/index.py to process it.',
  })
}

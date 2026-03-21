import { NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function POST() {
  const sb = serverClient()

  const { data } = await sb
    .from('indexing_jobs')
    .select('id, status')
    .order('id', { ascending: false })
    .limit(1)
    .single()

  if (!data || data.status !== 'running') {
    return NextResponse.json({ error: 'No running job to stop' }, { status: 409 })
  }

  await sb.from('indexing_jobs').update({ status: 'stop_requested' }).eq('id', data.id)
  return NextResponse.json({ ok: true, message: 'Stop requested — CLI will halt after current image' })
}

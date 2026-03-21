import { NextRequest, NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function POST(req: NextRequest, { params }: { params: Promise<{ clusterId: string }> }) {
  const { clusterId } = await params
  const body = await req.json().catch(() => ({}))
  const name = body.name?.trim()

  if (!name) return NextResponse.json({ error: 'name required' }, { status: 400 })

  const { error } = await serverClient()
    .from('person_clusters')
    .update({ name })
    .eq('id', parseInt(clusterId))

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true })
}

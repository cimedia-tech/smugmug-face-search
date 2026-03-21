import { NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function GET() {
  const { data, error } = await serverClient()
    .from('person_clusters_with_counts')
    .select('id, name, photo_count, sample_face_url')
    .order('photo_count', { ascending: false })

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  type Row = { id: number | null; name: string | null; photo_count: number | null; sample_face_url: string | null }
  const result = (data ?? [] as Row[]).map((c: Row) => ({
    id:              c.id ?? 0,
    name:            c.name ?? `Unknown #${c.id}`,
    photo_count:     c.photo_count ?? 0,
    sample_face_url: c.sample_face_url ?? null,
  }))

  return NextResponse.json(result)
}

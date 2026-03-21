import { NextRequest, NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ clusterId: string }> }) {
  const { clusterId } = await params

  const { data, error } = await serverClient()
    .from('face_index')
    .select('smugmug_image_key, thumbnail_url, image_url')
    .eq('cluster_id', parseInt(clusterId))

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  // Deduplicate by image key
  const seen = new Set<string>()
  const unique = (data ?? []).filter((r: { smugmug_image_key: string }) => {
    if (seen.has(r.smugmug_image_key)) return false
    seen.add(r.smugmug_image_key)
    return true
  })

  return NextResponse.json(unique)
}

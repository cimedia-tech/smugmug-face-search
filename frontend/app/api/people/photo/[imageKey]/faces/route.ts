import { NextRequest, NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ imageKey: string }> }) {
  const { imageKey } = await params

  const { data, error } = await serverClient()
    .from('face_index')
    .select('id, face_index_in_photo, bbox_x, bbox_y, bbox_w, bbox_h, cluster_id, face_crop_url, person_clusters(name)')
    .eq('smugmug_image_key', imageKey)

  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  type FaceRow = { id: number; face_index_in_photo: number; bbox_x: number | null; bbox_y: number | null; bbox_w: number | null; bbox_h: number | null; cluster_id: number | null; face_crop_url: string | null; person_clusters: { name: string | null } | null }
  const result = (data ?? [] as FaceRow[]).map((r: FaceRow) => ({
    face_id:      r.id,
    face_index:   r.face_index_in_photo,
    bbox:         { x: r.bbox_x, y: r.bbox_y, w: r.bbox_w, h: r.bbox_h },
    cluster_id:   r.cluster_id,
    name:         (r.person_clusters as any)?.name
                    ?? (r.cluster_id ? `Unknown #${r.cluster_id}` : 'Unmatched'),
    face_crop_url: r.face_crop_url,
  }))

  return NextResponse.json(result)
}

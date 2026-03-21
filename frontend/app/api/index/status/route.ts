import { NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function GET() {
  const { data } = await serverClient()
    .from('indexing_jobs')
    .select('status, total_images, indexed_count, last_image_key, error')
    .order('id', { ascending: false })
    .limit(1)
    .single()

  if (!data) return NextResponse.json({ status: 'idle', indexed: 0, total: 0 })

  return NextResponse.json({
    status:         data.status,
    indexed:        data.indexed_count,
    total:          data.total_images,
    last_image_key: data.last_image_key,
    error:          data.error,
  })
}

import { NextResponse } from 'next/server'
import { serverClient } from '@/lib/supabase'

export async function GET() {
  const sb = serverClient()
  const results: Record<string, any> = {}

  // Check each table exists and is accessible
  for (const table of ['oauth_tokens', 'oauth_pending', 'indexing_jobs', 'person_clusters', 'face_index']) {
    const { data, error } = await sb.from(table as any).select('*').limit(1)
    results[table] = error ? `ERROR: ${error.message}` : `OK (${data?.length ?? 0} rows)`
  }

  // Check env vars are set (not their values)
  results.env = {
    NEXT_PUBLIC_SUPABASE_URL:  !!process.env.NEXT_PUBLIC_SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY: !!process.env.SUPABASE_SERVICE_ROLE_KEY,
    SMUGMUG_API_KEY:           !!process.env.SMUGMUG_API_KEY,
    SMUGMUG_API_SECRET:        !!process.env.SMUGMUG_API_SECRET,
    CALLBACK_URL:              process.env.CALLBACK_URL,
    FRONTEND_URL:              process.env.FRONTEND_URL,
  }

  return NextResponse.json(results, { status: 200 })
}

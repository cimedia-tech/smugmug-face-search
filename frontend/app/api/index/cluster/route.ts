import { NextResponse } from 'next/server'

export async function POST() {
  return NextResponse.json(
    { message: 'Clustering runs locally. Run: python cli/cluster.py', status: 'cli_required' },
    { status: 202 }
  )
}

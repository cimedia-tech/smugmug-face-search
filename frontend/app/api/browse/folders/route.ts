import { NextRequest, NextResponse } from 'next/server'
import { getSmugMugClient } from '@/lib/auth'

function relPath(urlPath: string, userNick: string): string {
  const prefix = `/user/${userNick}/`
  return urlPath.startsWith(prefix) ? urlPath.slice(prefix.length) : urlPath.replace(/^\//, '')
}

export async function GET(req: NextRequest) {
  const path = new URL(req.url).searchParams.get('path') ?? ''

  try {
    const [client, user] = await getSmugMugClient()

    const [folders, albums] = await Promise.all([
      client.getFolders(user, path),
      client.getFolderAlbums(user, path),
    ])

    return NextResponse.json({
      path,
      folders: folders.map(f => ({ name: f.Name ?? '', path: relPath(f.UrlPath ?? '', user) })),
      albums:  albums.map(a => ({ name: a.Name ?? '', key: a.AlbumKey ?? '', image_count: a.ImageCount ?? 0 })),
    })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 401 })
  }
}

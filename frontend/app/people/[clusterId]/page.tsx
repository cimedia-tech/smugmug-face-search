'use client'
import { useEffect, useState } from 'react'
import PhotoGrid from '@/components/PhotoGrid'

interface Photo { smugmug_image_key: string; thumbnail_url: string; image_url: string }

export default function PersonDetail({ params }: { params: { clusterId: string } }) {
  const [name, setName] = useState('')
  const [editing, setEditing] = useState(false)
  const [photos, setPhotos] = useState<Photo[]>([])
  const id = params.clusterId

  useEffect(() => {
    fetch(`/api/people/${id}/photos`).then(r => r.json()).then(setPhotos)
    fetch('/api/people').then(r => r.json()).then((people: any[]) => {
      const p = people.find(x => String(x.id) === id)
      if (p) setName(p.name)
    })
  }, [id])

  const saveTag = async () => {
    await fetch(`/api/people/${id}/tag`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    setEditing(false)
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-6">
        <a href="/people" className="text-gray-400 hover:text-white text-sm">← People</a>
        {editing ? (
          <div className="flex gap-2">
            <input
              className="bg-gray-800 border border-gray-600 rounded px-3 py-1 text-white"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && saveTag()}
              autoFocus
            />
            <button onClick={saveTag} className="bg-green-600 hover:bg-green-500 px-3 py-1 rounded text-sm">Save</button>
            <button onClick={() => setEditing(false)} className="text-gray-400 hover:text-white px-2 py-1 text-sm">Cancel</button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{name}</h1>
            <button onClick={() => setEditing(true)} className="text-gray-400 hover:text-white text-sm">(edit)</button>
          </div>
        )}
        <span className="text-gray-500 text-sm ml-auto">{photos.length} photos</span>
      </div>
      <PhotoGrid photos={photos} />
    </main>
  )
}

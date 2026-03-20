'use client'
import { useEffect, useState, useRef } from 'react'
import FaceOverlay from '@/components/FaceOverlay'

interface Face {
  face_id: number
  bbox: { x: number; y: number; w: number; h: number }
  cluster_id: number | null
  name: string
  crop_b64: string | null
}

export default function GalleryPhoto({ params }: { params: Promise<{ imageKey: string }> }) {
  const [faces, setFaces] = useState<Face[]>([])
  const [imageUrl, setImageUrl] = useState('')
  const [key, setKey] = useState('')

  useEffect(() => {
    params.then(p => setKey(p.imageKey))
  }, [params])

  useEffect(() => {
    if (!key) return
    fetch(`/api/people/photo/${key}/faces`).then(r => r.json()).then(setFaces)
    const stored = sessionStorage.getItem(`img_${key}`)
    if (stored) setImageUrl(stored)
  }, [key])

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <a href="javascript:history.back()" className="text-gray-400 hover:text-white text-sm mb-4 inline-block">← Back</a>
      <FaceOverlay imageUrl={imageUrl} faces={faces} />
    </main>
  )
}

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

export default function GalleryPhoto({ params }: { params: { imageKey: string } }) {
  const [faces, setFaces] = useState<Face[]>([])
  const [imageUrl, setImageUrl] = useState('')

  const key = params.imageKey

  useEffect(() => {
    fetch(`/api/people/photo/${key}/faces`).then(r => r.json()).then(data => {
      setFaces(data)
    })
    // Get image URL from face data or fallback
    fetch(`/api/people/photo/${key}/faces`).then(r => r.json()).then((data: any[]) => {
      // image_url is not in faces endpoint — get from a people photo list is complex,
      // so we store it in session/localStorage when navigating from PhotoGrid
      const stored = sessionStorage.getItem(`img_${key}`)
      if (stored) setImageUrl(stored)
    })
  }, [key])

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <a href="javascript:history.back()" className="text-gray-400 hover:text-white text-sm mb-4 inline-block">← Back</a>
      <FaceOverlay imageUrl={imageUrl} faces={faces} />
    </main>
  )
}

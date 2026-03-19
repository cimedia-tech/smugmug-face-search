'use client'
import { useEffect, useRef } from 'react'
import Link from 'next/link'

interface Face {
  face_id: number
  bbox: { x: number; y: number; w: number; h: number }
  cluster_id: number | null
  name: string
}

interface Props {
  imageUrl: string
  faces: Face[]
}

export default function FaceOverlay({ imageUrl, faces }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  if (!imageUrl) {
    return <p className="text-gray-500">Image not available.</p>
  }

  return (
    <div ref={containerRef} className="relative inline-block w-full">
      <img src={imageUrl} alt="" className="w-full rounded-xl" />
      {faces.map(face => (
        <Link
          key={face.face_id}
          href={face.cluster_id ? `/people/${face.cluster_id}` : '#'}
          className="absolute border-2 border-yellow-400 hover:border-yellow-300 group"
          style={{
            left: `${face.bbox.x * 100}%`,
            top: `${face.bbox.y * 100}%`,
            width: `${face.bbox.w * 100}%`,
            height: `${face.bbox.h * 100}%`,
          }}
          title={face.name}
        >
          <span className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs px-1 py-0.5 truncate opacity-0 group-hover:opacity-100 transition-opacity">
            {face.name}
          </span>
        </Link>
      ))}
    </div>
  )
}

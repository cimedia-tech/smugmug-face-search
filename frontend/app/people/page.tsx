'use client'
import { useEffect, useState } from 'react'
import PersonCard from '@/components/PersonCard'

interface Person {
  id: number
  name: string
  photo_count: number
  sample_face_url: string | null
}

export default function PeoplePage() {
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/people')
      .then(r => r.json())
      .then(data => { setPeople(data); setLoading(false) })
  }, [])

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">People</h1>
        <div className="flex gap-4">
          <a href="/search" className="text-blue-400 hover:text-blue-300 text-sm">Search by Face</a>
          <a href="/" className="text-gray-400 hover:text-white text-sm">← Home</a>
        </div>
      </div>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : people.length === 0 ? (
        <p className="text-gray-500">No people found. Run indexing and clustering first.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {people.map(p => <PersonCard key={p.id} person={p} />)}
        </div>
      )}
    </main>
  )
}

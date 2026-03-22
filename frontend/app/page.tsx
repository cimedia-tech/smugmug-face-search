'use client'
import { useEffect, useState } from 'react'
import IndexStatus from '@/components/IndexStatus'

interface AuthStatus {
  connected: boolean
  user?: string
}

export default function Home() {
  const [auth, setAuth] = useState<AuthStatus | null>(null)

  useEffect(() => {
    fetch('/api/auth/status').then(r => r.json()).then(setAuth)
  }, [])

  return (
    <main className="max-w-2xl mx-auto px-4 py-16">
      <h1 className="text-3xl font-bold mb-2">SmugMug Face Search</h1>
      <p className="text-gray-400 mb-8">Browse your photos by person — like Google Photos, for SmugMug.</p>

      {!auth ? (
        <p className="text-gray-500">Checking connection...</p>
      ) : !auth.connected ? (
        <a
          href="/api/auth/start"
          className="inline-block bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg font-medium"
        >
          Connect SmugMug
        </a>
      ) : (
        <div className="space-y-6">
          <p className="text-green-400">Connected as <strong>{auth.user}</strong></p>
          <IndexStatus />
          <div className="flex gap-3">
            <a
              href="/people"
              className="inline-block bg-purple-600 hover:bg-purple-500 px-6 py-3 rounded-lg font-medium"
            >
              Browse People →
            </a>
            <a
              href="/search"
              className="inline-block bg-blue-700 hover:bg-blue-600 px-6 py-3 rounded-lg font-medium"
            >
              Search by Face →
            </a>
          </div>
        </div>
      )}
    </main>
  )
}

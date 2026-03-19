'use client'
import { useEffect, useState } from 'react'

interface Status {
  status: string
  indexed: number
  total: number
  error?: string
}

export default function IndexStatus() {
  const [status, setStatus] = useState<Status | null>(null)
  const [clustering, setClustering] = useState(false)

  const poll = () => {
    fetch('/api/index/status').then(r => r.json()).then(setStatus)
  }

  useEffect(() => {
    poll()
    const t = setInterval(poll, 3000)
    return () => clearInterval(t)
  }, [])

  const startIndex = async () => {
    await fetch('/api/index/start', { method: 'POST' })
    poll()
  }

  const startCluster = async () => {
    setClustering(true)
    await fetch('/api/index/cluster', { method: 'POST' })
    setClustering(false)
  }

  if (!status) return null

  const pct = status.total > 0 ? Math.round((status.indexed / status.total) * 100) : 0

  return (
    <div className="bg-gray-900 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-300">Indexing</span>
        <span className="text-xs text-gray-500 capitalize">{status.status}</span>
      </div>

      {status.total > 0 && (
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{status.indexed} / {status.total} photos</span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {status.error && <p className="text-red-400 text-xs">{status.error}</p>}

      <div className="flex gap-2">
        <button
          onClick={startIndex}
          disabled={status.status === 'running'}
          className="flex-1 bg-blue-700 hover:bg-blue-600 disabled:opacity-50 px-3 py-2 rounded text-sm"
        >
          {status.status === 'running' ? 'Indexing...' : 'Start Indexing'}
        </button>
        <button
          onClick={startCluster}
          disabled={clustering || status.indexed === 0}
          className="flex-1 bg-purple-700 hover:bg-purple-600 disabled:opacity-50 px-3 py-2 rounded text-sm"
        >
          {clustering ? 'Clustering...' : 'Cluster Faces'}
        </button>
      </div>
    </div>
  )
}

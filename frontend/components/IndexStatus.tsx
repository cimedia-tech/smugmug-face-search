'use client'
import { useEffect, useRef, useState } from 'react'

function playDoneSound(success: boolean) {
  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
  const notes = success
    ? [523, 659, 784, 1047]   // C E G C — pleasant ascending chord
    : [400, 300]               // descending drop for failure

  notes.forEach((freq, i) => {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.type = 'sine'
    osc.frequency.value = freq
    const t = ctx.currentTime + i * 0.18
    gain.gain.setValueAtTime(0.4, t)
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.4)
    osc.start(t)
    osc.stop(t + 0.4)
  })
}

function notifyDone(success: boolean) {
  playDoneSound(success)
  if (Notification.permission === 'granted') {
    new Notification(
      success ? '✅ Indexing complete' : '❌ Indexing failed',
      { body: success ? 'Face indexing finished. You can now cluster.' : 'Check the error log.' }
    )
  }
}

interface Status {
  status: string
  indexed: number
  total: number
  error?: string
}

interface FolderItem { name: string; path: string }
interface AlbumItem  { name: string; key: string; image_count: number }
interface BrowseResult { path: string; folders: FolderItem[]; albums: AlbumItem[] }

type Selection =
  | { type: 'all' }
  | { type: 'folder'; path: string; label: string }
  | { type: 'albums'; keys: string[]; label: string }

export default function IndexStatus() {
  const [status, setStatus]         = useState<Status | null>(null)
  const [clustering, setClustering] = useState(false)
  const [picking, setPicking]       = useState(false)
  const [browse, setBrowse]         = useState<BrowseResult | null>(null)
  const [browseStack, setBrowseStack] = useState<string[]>([])
  const [selection, setSelection]   = useState<Selection>({ type: 'all' })
  const [selectedAlbums, setSelectedAlbums] = useState<Set<string>>(new Set())
  const prevStatusRef = useRef<string | null>(null)

  useEffect(() => {
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  const poll = () => {
    fetch('/api/index/status').then(r => r.json()).then((s: Status) => {
      const prev = prevStatusRef.current
      if (prev === 'running' && s.status === 'done')   notifyDone(true)
      if (prev === 'running' && s.status === 'failed') notifyDone(false)
      prevStatusRef.current = s.status
      setStatus(s)
    })
  }

  useEffect(() => {
    poll()
    const t = setInterval(poll, 3000)
    return () => clearInterval(t)
  }, [])

  const openPicker = async () => {
    setPicking(true)
    setBrowseStack([])
    setSelectedAlbums(new Set())
    await loadBrowse('')
  }

  const loadBrowse = async (path: string) => {
    const r = await fetch(`/api/browse/folders?path=${encodeURIComponent(path)}`)
    const data: BrowseResult = await r.json()
    setBrowse(data)
  }

  const enterFolder = async (path: string) => {
    setBrowseStack(s => [...s, browse?.path ?? ''])
    await loadBrowse(path)
  }

  const goBack = async () => {
    const prev = browseStack[browseStack.length - 1] ?? ''
    setBrowseStack(s => s.slice(0, -1))
    await loadBrowse(prev)
  }

  const toggleAlbum = (key: string) => {
    setSelectedAlbums(s => {
      const next = new Set(s)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const confirmSelection = () => {
    if (selectedAlbums.size > 0) {
      const names = browse?.albums
        .filter(a => selectedAlbums.has(a.key))
        .map(a => a.name).join(', ') ?? ''
      setSelection({ type: 'albums', keys: [...selectedAlbums], label: names })
    } else if (browse && browse.path) {
      setSelection({ type: 'folder', path: browse.path, label: browse.path })
    } else {
      setSelection({ type: 'all' })
    }
    setPicking(false)
  }

  const startIndex = async () => {
    const body =
      selection.type === 'folder'  ? { folder_path: selection.path } :
      selection.type === 'albums'  ? { album_keys: selection.keys } :
      {}
    await fetch('/api/index/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    poll()
  }

  const stopIndex = async () => {
    await fetch('/api/index/stop', { method: 'POST' })
    poll()
  }

  const startCluster = async () => {
    setClustering(true)
    const r = await fetch('/api/index/cluster', { method: 'POST' })
    setClustering(false)
    if (r.status === 202) {
      alert('Clustering runs locally.\n\nRun this in your terminal:\n  python cli/cluster.py')
    }
  }

  if (!status) return null

  const pct = status.total > 0 ? Math.round((status.indexed / status.total) * 100) : 0
  const scopeLabel =
    selection.type === 'all'    ? 'Entire account' :
    selection.type === 'folder' ? `Folder: ${selection.label}` :
                                  `Albums: ${selection.label}`

  return (
    <div className="bg-gray-900 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-300">Indexing</span>
        <span className="text-xs text-gray-500 capitalize">{status.status}</span>
      </div>

      {/* Scope selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400 truncate flex-1">{scopeLabel}</span>
        <button
          onClick={openPicker}
          disabled={status.status === 'running'}
          className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-40 shrink-0"
        >
          Change scope
        </button>
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
        {status.status === 'running' ? (
          <button
            onClick={stopIndex}
            className="flex-1 bg-red-700 hover:bg-red-600 px-3 py-2 rounded text-sm"
          >
            Stop
          </button>
        ) : (
          <button
            onClick={startIndex}
            className="flex-1 bg-blue-700 hover:bg-blue-600 px-3 py-2 rounded text-sm"
          >
            Start Indexing
          </button>
        )}
        <button
          onClick={startCluster}
          disabled={clustering || status.indexed === 0}
          className="flex-1 bg-purple-700 hover:bg-purple-600 disabled:opacity-50 px-3 py-2 rounded text-sm"
        >
          {clustering ? 'Clustering...' : 'Cluster Faces'}
        </button>
      </div>

      {/* Folder/Album picker modal */}
      {picking && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center gap-2 p-4 border-b border-gray-800">
              {browseStack.length > 0 && (
                <button onClick={goBack} className="text-gray-400 hover:text-white text-sm">←</button>
              )}
              <span className="text-sm font-medium flex-1 truncate">
                {browse?.path ? `/${browse.path}` : 'Your SmugMug'}
              </span>
              <button onClick={() => setPicking(false)} className="text-gray-500 hover:text-white text-lg leading-none">×</button>
            </div>

            {/* Content */}
            <div className="overflow-y-auto flex-1 p-2">
              {!browse ? (
                <p className="text-gray-500 text-sm p-4">Loading...</p>
              ) : (
                <>
                  {/* Folders */}
                  {browse.folders.map(f => (
                    <button
                      key={f.path}
                      onClick={() => enterFolder(f.path)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-gray-800 text-left"
                    >
                      <span className="text-gray-400">📁</span>
                      <span className="text-sm flex-1">{f.name}</span>
                      <span className="text-gray-600 text-xs">→</span>
                    </button>
                  ))}

                  {/* Albums with checkboxes */}
                  {browse.albums.map(a => (
                    <label
                      key={a.key}
                      className="flex items-center gap-3 px-3 py-2 rounded hover:bg-gray-800 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAlbums.has(a.key)}
                        onChange={() => toggleAlbum(a.key)}
                        className="accent-blue-500"
                      />
                      <span className="text-sm flex-1">{a.name}</span>
                      <span className="text-gray-500 text-xs">{a.image_count} photos</span>
                    </label>
                  ))}

                  {browse.folders.length === 0 && browse.albums.length === 0 && (
                    <p className="text-gray-500 text-sm p-4">Empty folder</p>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-800 flex gap-2">
              <button
                onClick={() => { setSelection({ type: 'all' }); setPicking(false) }}
                className="flex-1 text-sm text-gray-400 hover:text-white py-2"
              >
                Index entire account
              </button>
              <button
                onClick={confirmSelection}
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-sm py-2 rounded"
              >
                {selectedAlbums.size > 0
                  ? `Index ${selectedAlbums.size} album${selectedAlbums.size > 1 ? 's' : ''}`
                  : browse?.path
                    ? `Index folder "${browse.path}"`
                    : 'Index all'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

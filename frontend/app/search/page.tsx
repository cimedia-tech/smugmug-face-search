'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { createClient } from '@/lib/supabase'

interface SearchResult {
  image_key:    string
  image_url:    string | null
  thumbnail_url: string | null
  face_crop_url: string | null
  score:        number
}

type JobStatus = 'idle' | 'uploading' | 'pending' | 'running' | 'done' | 'failed'

export default function SearchPage() {
  const [preview, setPreview]   = useState<string | null>(null)
  const [jobId, setJobId]       = useState<number | null>(null)
  const [status, setStatus]     = useState<JobStatus>('idle')
  const [results, setResults]   = useState<SearchResult[]>([])
  const [errMsg, setErrMsg]     = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPoll = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  useEffect(() => () => stopPoll(), [])

  const pollJob = useCallback((id: number) => {
    stopPoll()
    pollRef.current = setInterval(async () => {
      const r = await fetch(`/api/search/${id}`)
      if (!r.ok) return
      const data = await r.json()
      setStatus(data.status)
      if (data.status === 'done') {
        setResults(data.results ?? [])
        stopPoll()
      } else if (data.status === 'failed') {
        setErrMsg(data.error ?? 'Search failed')
        stopPoll()
      }
    }, 2500)
  }, [])

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setErrMsg('Please upload an image file.')
      return
    }

    // Show preview
    const objectUrl = URL.createObjectURL(file)
    setPreview(objectUrl)
    setResults([])
    setErrMsg(null)
    setJobId(null)
    setStatus('uploading')

    try {
      // Upload directly to Supabase Storage from the browser
      const sb       = createClient()
      const filename = `search/${Date.now()}_${file.name.replace(/[^a-z0-9.]/gi, '_')}`
      const { error: upErr } = await sb.storage.from('faces').upload(filename, file, {
        contentType: file.type,
        upsert: false,
      })
      if (upErr) throw new Error(`Upload failed: ${upErr.message}`)

      const { data: urlData } = sb.storage.from('faces').getPublicUrl(filename)
      const imageUrl = urlData.publicUrl

      // Create search job
      const jobRes = await fetch('/api/search', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ image_url: imageUrl }),
      })
      if (!jobRes.ok) throw new Error('Failed to create search job')
      const { id } = await jobRes.json()

      setJobId(id)
      setStatus('pending')
      pollJob(id)
    } catch (e: any) {
      setErrMsg(e.message)
      setStatus('failed')
    }
  }, [pollJob])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const reset = () => {
    stopPoll()
    setPreview(null)
    setJobId(null)
    setStatus('idle')
    setResults([])
    setErrMsg(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const statusLabel: Record<JobStatus, string> = {
    idle:      '',
    uploading: 'Uploading image...',
    pending:   'Queued — run: python cli/search.py',
    running:   'Searching faces...',
    done:      `Found ${results.length} match${results.length !== 1 ? 'es' : ''}`,
    failed:    '',
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Search by Face</h1>
        <a href="/people" className="text-gray-400 hover:text-white text-sm">← People</a>
      </div>

      {/* Upload zone */}
      {status === 'idle' && (
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
          className={`
            border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-colors
            ${dragging ? 'border-blue-400 bg-blue-950/30' : 'border-gray-700 hover:border-gray-500'}
          `}
        >
          <p className="text-4xl mb-3">🔍</p>
          <p className="text-gray-300 font-medium">Drop a photo here, or click to browse</p>
          <p className="text-gray-500 text-sm mt-1">Upload any photo containing a face to find similar photos</p>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFileChange} />
        </div>
      )}

      {/* Preview + status */}
      {preview && (
        <div className="flex gap-6 items-start mb-6">
          <div className="shrink-0">
            <img src={preview} alt="Query" className="w-32 h-32 object-cover rounded-lg border border-gray-700" />
          </div>
          <div className="flex-1 pt-2">
            {statusLabel[status] && (
              <p className={`text-sm font-medium mb-1 ${
                status === 'done'   ? 'text-green-400' :
                status === 'failed' ? 'text-red-400'   : 'text-blue-400'
              }`}>
                {statusLabel[status]}
              </p>
            )}
            {(status === 'pending' || status === 'running') && (
              <p className="text-xs text-gray-500 mt-1">
                Waiting for the local CLI to process this search.
                <br />Open a terminal and run:{' '}
                <code className="bg-gray-800 px-1 rounded">python cli/search.py</code>
              </p>
            )}
            {errMsg && <p className="text-red-400 text-sm">{errMsg}</p>}
            <button onClick={reset} className="mt-3 text-xs text-gray-500 hover:text-white underline">
              Search again
            </button>
          </div>
        </div>
      )}

      {/* Results grid */}
      {results.length > 0 && (
        <>
          <h2 className="text-lg font-semibold mb-4 text-gray-200">Best matches</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {results.map(r => (
              <a
                key={r.image_key}
                href={r.image_url ?? '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="group relative block rounded-lg overflow-hidden border border-gray-800 hover:border-blue-500 transition-colors"
              >
                <img
                  src={r.thumbnail_url ?? r.image_url ?? ''}
                  alt=""
                  className="w-full aspect-square object-cover"
                />
                {/* Score badge */}
                <div className="absolute bottom-1 right-1 bg-black/70 text-xs px-1.5 py-0.5 rounded text-gray-300">
                  {Math.round(r.score * 100)}%
                </div>
                {/* Face crop overlay on hover */}
                {r.face_crop_url && (
                  <div className="absolute top-1 left-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <img
                      src={r.face_crop_url}
                      alt="face"
                      className="w-10 h-10 rounded border border-white/30 object-cover"
                    />
                  </div>
                )}
              </a>
            ))}
          </div>
        </>
      )}

      {status === 'done' && results.length === 0 && (
        <p className="text-gray-500 text-center py-12">No matches found — try a different photo.</p>
      )}
    </main>
  )
}

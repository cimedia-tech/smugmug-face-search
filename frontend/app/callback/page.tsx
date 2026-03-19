'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Callback() {
  const router = useRouter()
  useEffect(() => { router.push('/') }, [router])
  return <p className="p-8 text-gray-400">Completing sign-in...</p>
}

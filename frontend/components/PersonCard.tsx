import Link from 'next/link'

interface Person {
  id: number
  name: string
  photo_count: number
  sample_face_url: string | null
}

export default function PersonCard({ person }: { person: Person }) {
  return (
    <Link href={`/people/${person.id}`} className="group flex flex-col items-center gap-2">
      <div className="w-20 h-20 rounded-full overflow-hidden bg-gray-800 flex items-center justify-center">
        {person.sample_face_url ? (
          <img
            src={person.sample_face_url}
            alt={person.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
          />
        ) : (
          <span className="text-3xl">👤</span>
        )}
      </div>
      <div className="text-center">
        <p className="text-sm font-medium truncate max-w-[90px]">{person.name}</p>
        <p className="text-xs text-gray-500">{person.photo_count} photos</p>
      </div>
    </Link>
  )
}

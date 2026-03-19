'use client'

interface Photo {
  smugmug_image_key: string
  thumbnail_url: string
  image_url: string
}

export default function PhotoGrid({ photos }: { photos: Photo[] }) {
  const openPhoto = (photo: Photo) => {
    sessionStorage.setItem(`img_${photo.smugmug_image_key}`, photo.image_url)
    window.location.href = `/gallery/${photo.smugmug_image_key}`
  }

  if (photos.length === 0) {
    return <p className="text-gray-500">No photos found.</p>
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
      {photos.map(p => (
        <button
          key={p.smugmug_image_key}
          onClick={() => openPhoto(p)}
          className="aspect-square overflow-hidden rounded-lg bg-gray-800 hover:opacity-80 transition-opacity"
        >
          <img
            src={p.thumbnail_url}
            alt=""
            className="w-full h-full object-cover"
          />
        </button>
      ))}
    </div>
  )
}

"""Check if face_index rows actually have embeddings."""
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# Check how many rows have non-null embeddings
r = sb.table('face_index') \
    .select('id, face_embedding, smugmug_image_key') \
    .not_.is_('face_embedding', 'null') \
    .limit(3) \
    .execute()

print(f"Rows with non-null face_embedding: {len(r.data)} (sample of first 3)")
for row in r.data:
    emb = row.get('face_embedding')
    emb_type = type(emb).__name__
    emb_len = len(emb) if isinstance(emb, (list, str, bytes)) else 'n/a'
    print(f"  id={row['id']}  embedding type={emb_type}  len={emb_len}")

# Count total with embeddings
r2 = sb.table('face_index').select('id', count='exact').not_.is_('face_embedding', 'null').execute()
print(f"\nTotal rows with non-null embedding: {r2.count}")

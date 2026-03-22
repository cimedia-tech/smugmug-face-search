"""Check face_index and indexing_jobs status in Supabase."""
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# Count indexed faces
r = sb.table('face_index').select('id', count='exact').execute()
print(f"face_index total rows: {r.count}")

# Check recent indexing jobs
r2 = sb.table('indexing_jobs').select('id, status, progress, error, albums').order('id', desc=True).limit(5).execute()
print("\nRecent indexing_jobs:")
for row in r2.data:
    print(f"  Job {row['id']}: status={row['status']}  progress={row.get('progress')}  albums={row.get('albums')}")

"""Show image URLs from search jobs so we can inspect what was uploaded."""
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
r = sb.table('search_jobs').select('id, status, image_url, error').order('id', desc=True).limit(5).execute()
for row in r.data:
    print(f"Job {row['id']}: {row['status']}")
    print(f"  image_url: {row['image_url']}")
    print(f"  error: {row.get('error')}")

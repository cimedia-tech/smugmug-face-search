"""Reset failed search jobs back to pending."""
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
result = sb.table('search_jobs').update({'status': 'pending', 'error': None}) \
    .in_('status', ['failed', 'running', 'queued']) \
    .execute()
print(f"Reset {len(result.data)} job(s) back to pending.")
for row in result.data:
    print(f"  Job {row['id']} reset")

from supabase import create_client, Client
from ..core.config import settings

_supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

def get_supabase() -> Client:
    """
    Get the Supabase client instance.
    """
    return _supabase



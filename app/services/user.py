from app.db.session import get_supabase
import re

class UserService:
    @staticmethod
    async def get_by_slug(slug: str):
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("slug", slug).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def update_slug(user_id: str, slug: str):
        # Validate slug format
        if not re.match(r'^[a-z0-9-]+$', slug):
            raise ValueError("Invalid slug format")
        
        supabase = get_supabase()
        result = supabase.table("users")\
            .update({"slug": slug, "updated_at": "now()"})\
            .eq("id", user_id)\
            .execute()
            
        return result.data[0] if result.data else None
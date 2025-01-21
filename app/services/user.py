# services/user.py
from app.db.session import get_supabase
import re
from typing import Optional, Dict, Any

class UserService:
    @staticmethod
    async def get_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("slug", slug).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def check_slug_availability(slug: str) -> bool:
        supabase = get_supabase()
        result = supabase.table("users").select("id").eq("slug", slug).execute()
        return len(result.data) == 0

    @staticmethod
    async def update_slug(user_id: str, slug: str) -> Optional[Dict[str, Any]]:
        # Validate slug format
        if not re.match(r'^[a-z0-9-]+$', slug):
            raise ValueError("Invalid slug format")
        
        # Check if slug is already taken
        is_available = await UserService.check_slug_availability(slug)
        if not is_available:
            raise ValueError("Slug already taken")

        supabase = get_supabase()
        result = supabase.table("users")\
            .update({"slug": slug, "updated_at": "now()"})\
            .eq("id", user_id)\
            .execute()
        
        return result.data[0] if result.data else None
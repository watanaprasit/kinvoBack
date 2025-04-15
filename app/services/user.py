from app.db.session import get_supabase
import re
from typing import Optional, Dict, Any
from fastapi import HTTPException
from pydantic import BaseModel

class UserService:
    @staticmethod
    async def get_by_email(email: str):
        try:
            supabase = get_supabase()
            response = (
                supabase.table("users")
                .select("*")
                .eq("email", email)
                .single()
                .execute()
            )
            
            if not response.data:
                raise HTTPException(status_code=404, detail="User not found")
                
            return response.data
        except Exception as e:
            print(f"Error in get_by_email: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
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
    
    @staticmethod
    def get_user_by_id(user_id: str):
        supabase = get_supabase()
        result = supabase.from_("users").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def get_current_user_by_token(token: str) -> Dict[str, Any]:
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("email", token).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")
        
        return result.data
    
class UserPublicProfileResponse(BaseModel):
    display_name: str
    slug: str
    title: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    website: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None

class UserPublicResponse(BaseModel):
    full_name: str
    slug: str
    profile: UserPublicProfileResponse
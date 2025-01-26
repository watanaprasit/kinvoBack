from app.db.session import get_supabase
from app.schemas.user.profile import UserProfileCreate, UserProfileUpdate
from typing import Optional, Dict, Any
from app.services.user import UserService
from fastapi import UploadFile, HTTPException
import uuid
from datetime import datetime

class UserProfileService:
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).single().execute()

        return response.data
        
        

    @staticmethod
    async def update_profile(user_id: str, profile_data: UserProfileUpdate, photo: UploadFile = None, current_user=None) -> Dict[str, Any]:
        supabase = get_supabase()
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Explicit type conversion and stripping
        update_data = {}
        if profile_data.display_name is not None:
            update_data['display_name'] = profile_data.display_name.strip()
        if profile_data.slug is not None:
            update_data['slug'] = profile_data.slug.strip()
        if profile_data.photo_url is not None:
            update_data['photo_url'] = profile_data.photo_url.strip()
        
        print(f"Current User ID: {current_user.id}")
        print(f"Prepared Update Data: {update_data}")
        
        try:
            result = (
                supabase.table("user_profiles")
                .update(update_data)
                .eq("user_id", current_user.id)
                .execute()
            )
            
            print(f"Update Result: {result}")
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Profile not found or no changes made")
            
            return result.data[0]
        
        except Exception as e:
            print(f"Update Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @staticmethod
    async def create_profile(user_id: int, profile_data: UserProfileCreate, profile_id: Optional[int] = None) -> Dict[str, Any]:
        supabase = get_supabase()
        
        insert_data = {
            "id": profile_id,
            "user_id": user_id,
            "display_name": profile_data.display_name,
            "slug": profile_data.slug,
            "photo_url": profile_data.photo_url,
        }
        
        # Remove None values
        insert_data = {k: v for k, v in insert_data.items() if v is not None}
        
        # Use .execute() and return first data item
        result = await supabase.table("user_profiles").insert(insert_data).execute()
        
        return result.data[0] if result.data else None
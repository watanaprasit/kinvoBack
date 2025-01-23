from app.db.session import get_supabase
from app.schemas.user import UserProfileCreate, UserProfileUpdate
from typing import Optional
from fastapi import UploadFile
from uuid import UUID

class UserProfileService:
    @staticmethod
    async def get_by_user_id(user_id: str) -> Optional[dict]:
        supabase = get_supabase()
        result = await supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def update_profile(user_id: str, profile_data: UserProfileUpdate, photo: UploadFile = None) -> dict:
        supabase = get_supabase()
        update_data = profile_data.dict(exclude_unset=True)
        if photo:
            update_data["photo_url"] = await UserProfileService.upload_photo(photo)
        result = await supabase.table("user_profiles").update(update_data).eq("user_id", user_id).execute()
        return result.data[0]

    @staticmethod
    async def upload_photo(photo: UploadFile) -> str:
        supabase = get_supabase()
        bucket_name = "avatars"
        file_name = photo.filename
        res = await supabase.storage().from_(bucket_name).upload(file_name, photo.file)
        return supabase.storage().from_(bucket_name).get_public_url(file_name)
    
    
    
    
    @staticmethod
    async def create_profile(user_id: str, profile_data: UserProfileCreate) -> dict:
        supabase = get_supabase()
        
        # Convert integer ID to UUID string
        uuid_str = f"{user_id:032x}"  # Convert integer to 32-character hex string
        
        result = await supabase.table("user_profiles").insert({
            "id": uuid_str,
            "user_id": uuid_str,
            "display_name": profile_data.display_name,
            "slug": profile_data.slug,
            "photo_url": profile_data.photo_url
        }).execute()
        return result.data[0]
from app.db.session import get_supabase
from app.schemas.user import UserProfileCreate, UserProfileUpdate
from typing import Optional, Dict, Any
from fastapi import UploadFile
import uuid

class UserProfileService:
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).single().execute()

        return response.data
        
        

    @staticmethod
    async def update_profile(user_id: str, profile_data: UserProfileUpdate, photo: UploadFile = None) -> Dict[str, Any]:
        supabase = get_supabase()
        update_data = profile_data.model_dump(exclude_unset=True)
        
        if photo:
            update_data["photo_url"] = await UserProfileService.upload_photo(photo)
        
        result = await supabase.table("user_profiles").update(update_data).eq("user_id", user_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def upload_photo(photo: UploadFile) -> str:
        supabase = get_supabase()
        bucket_name = "avatars"
        file_name = f"{uuid.uuid4()}_{photo.filename}"
        
        # Upload the file
        res = await supabase.storage().from_(bucket_name).upload(file_name, photo.file)
        
        # Get public URL
        return supabase.storage().from_(bucket_name).get_public_url(file_name)

    @staticmethod
    async def create_profile(user_id: str, profile_data: UserProfileCreate) -> Dict[str, Any]:
        supabase = get_supabase()
        
        # Generate a new UUID for the profile
        profile_uuid = str(uuid.uuid4())
        
        # Prepare insert data
        insert_data = {
            "id": profile_uuid,
            "user_id": user_id,
            "display_name": profile_data.display_name,
            "slug": profile_data.slug,
            "photo_url": profile_data.photo_url,
            "created_at": "now()",
            "updated_at": "now()"
        }
        
        # Remove None values
        insert_data = {k: v for k, v in insert_data.items() if v is not None}
        
        result = await supabase.table("user_profiles").insert(insert_data).execute()
        
        return result.data[0] if result.data else None
from app.db.session import get_supabase
from app.schemas.user.profile import UserProfileCreate, UserProfileUpdate
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
import uuid
from datetime import datetime
import io

class UserProfileService:
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).single().execute()
        
        if response.data and response.data.get('photo_url'):
            # Get just the file path without query parameters
            file_path = response.data['photo_url'].split('?')[0].split('/')[-1]
            
            # Get fresh public URL
            public_url = supabase.storage.from_("user_profile_photos").get_public_url(file_path)
            response.data['photo_url'] = public_url
            
        return response.data

    @staticmethod
    async def _handle_photo_upload(user_id: int, photo: UploadFile) -> str:
        try:
            # Read file content
            contents = await photo.read()
            file_extension = photo.filename.split('.')[-1].lower()
            
            # Create user-specific folder path and filename
            user_folder = str(user_id)
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            full_path = f"{user_folder}/{unique_filename}"
            
            supabase = get_supabase()
            
            # Delete existing photo if any
            existing_profile = await UserProfileService.get_by_user_id(user_id)
            if existing_profile and existing_profile.get('photo_url'):
                old_file = existing_profile['photo_url'].split('/')[-1].split('?')[0]
                old_path = f"{user_folder}/{old_file}"
                try:
                    supabase.storage.from_('user_profile_photos').remove(old_path)
                except Exception as e:
                    print(f"Warning: Failed to delete old photo: {str(e)}")
            
            # Upload new photo with user folder structure
            upload_response = supabase.storage.from_('user_profile_photos').upload(
                path=full_path,  # Using the full path with user folder
                file=contents,
                file_options={
                    "content-type": photo.content_type,
                    "cache-control": "3600"
                }
            )
            
            if hasattr(upload_response, 'error') and upload_response.error:
                raise Exception(f"Upload failed: {upload_response.error}")
            
            # Get public URL without query parameters
            public_url = supabase.storage.from_('user_profile_photos').get_public_url(full_path)
            
            print(f"Successfully uploaded photo: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"Photo upload error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")

    @staticmethod
    async def update_profile(user_id: str, profile_data: UserProfileUpdate, photo: UploadFile = None, current_user=None) -> Dict[str, Any]:
        supabase = get_supabase()
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        try:
            user_id_int = int(current_user.id)
            
            # Get existing profile
            existing_profile = await UserProfileService.get_by_user_id(user_id_int)
            
            if not existing_profile:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            # Handle photo upload if provided
            photo_url = None
            if photo:
                photo_url = await UserProfileService._handle_photo_upload(user_id_int, photo)
            
            # Prepare update data
            update_data = {}
            if profile_data.display_name is not None:
                update_data['display_name'] = profile_data.display_name.strip()
            if profile_data.slug is not None:
                update_data['slug'] = profile_data.slug.strip()
            if photo_url:
                update_data['photo_url'] = photo_url
            
            if not update_data:
                return existing_profile
            
            # Update the profile
            result = (
                supabase.table("user_profiles")
                .update(update_data)
                .eq("user_id", user_id_int)
                .execute()
            )
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            updated_profile = result.data[0]
            
            # Ensure photo_url is a fresh public URL
            if updated_profile.get('photo_url'):
                file_path = updated_profile['photo_url'].split('?')[0].split('/')[-1]
                updated_profile['photo_url'] = supabase.storage.from_('user_profile_photos').get_public_url(file_path)
            
            return updated_profile
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid user ID format: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

    @staticmethod
    async def create_profile(
        user_id: int, 
        profile_data: UserProfileCreate, 
        photo: Optional[UploadFile] = None
    ) -> Dict[str, Any]:
        supabase = get_supabase()
        
        # Handle photo upload if provided
        photo_url = None
        if photo:
            photo_url = await UserProfileService._handle_photo_upload(user_id, photo)

        try:
            # Insert a new record, let the database handle the auto-incrementing id
            result = await supabase.table("user_profiles").insert({
                "user_id": user_id,
                "display_name": profile_data.display_name,
                "slug": profile_data.slug,
                "photo_url": photo_url or profile_data.photo_url
            }, returning="*").execute()
            
            if result.data:
                return result.data[0]
            else:
                raise HTTPException(status_code=500, detail="Failed to create user profile")
        
        except Exception as e:
            print(f"Insertion error: {e}")
            raise

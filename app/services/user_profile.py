from app.db.session import get_supabase
from app.schemas.user.profile import UserProfileCreate, UserProfileUpdate
from typing import Optional, Dict, Any
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
    async def _handle_photo_upload(user_id: int, photo: UploadFile) -> str:
        contents = await photo.read()
        unique_filename = f"{user_id}_{uuid.uuid4().hex}"
        try:
            supabase = get_supabase()
            upload_response = supabase.storage.from_('user_profile_photos').upload(
                file=contents,
                path=unique_filename,
                file_options={"content-type": photo.content_type}
            )
            
            if hasattr(upload_response, 'error') and upload_response.error:
                raise Exception(f"Upload failed: {upload_response.error}")
                
            # Get public URL
            url = supabase.storage.from_('user_profile_photos').get_public_url(unique_filename)
            if not url:
                raise Exception("Failed to get public URL")
                
            return url
        
        except Exception as e:
            print(f"Photo upload error: {str(e)}")  # Add logging
            raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")

    @staticmethod
    async def update_profile(user_id: str, profile_data: UserProfileUpdate, photo: UploadFile = None, current_user=None) -> Dict[str, Any]:
        supabase = get_supabase()
        
        print(f"Starting profile update for user {user_id}")
        print(f"Received data: display_name={profile_data.display_name}, slug={profile_data.slug}")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        try:
            user_id_int = int(current_user.id)
            
            # Get existing profile
            existing_profile = await UserProfileService.get_by_user_id(user_id_int)
            print(f"Existing profile: {existing_profile}")
            
            if not existing_profile:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            # Handle photo upload if provided
            photo_url = None
            if photo:
                print(f"Processing photo upload: {photo.filename}")
                try:
                    photo_url = await UserProfileService._handle_photo_upload(user_id_int, photo)
                    print(f"Photo uploaded successfully: {photo_url}")
                except Exception as e:
                    print(f"Photo upload failed: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")
            
            # Prepare update data with explicit checks
            update_data = {}
            if profile_data.display_name is not None:
                update_data['display_name'] = profile_data.display_name.strip()
            if profile_data.slug is not None:
                update_data['slug'] = profile_data.slug.strip()
            if photo_url:
                update_data['photo_url'] = photo_url
            
            print(f"Update data prepared: {update_data}")
            
            if not update_data:
                print("No updates requested")
                return existing_profile
            
            # Perform the update with explicit error handling
            try:
                result = (
                    supabase.table("user_profiles")
                    .update(update_data)
                    .eq("user_id", user_id_int)
                    .execute()
                )
                print(f"Update result: {result.data}")
                
                if not result.data:
                    print("Update returned no data")
                    check_profile = await UserProfileService.get_by_user_id(user_id_int)
                    if check_profile:
                        return check_profile
                    raise HTTPException(status_code=404, detail="Profile not found during update")
                
                return result.data[0]
                
            except Exception as e:
                print(f"Supabase update error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")
                
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

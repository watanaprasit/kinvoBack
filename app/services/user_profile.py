from app.db.session import get_supabase
from app.schemas.user.profile import UserProfileCreate, UserProfileUpdate
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
import uuid

class UserProfileService:
    @staticmethod
    def _clean_url(url: str) -> str:
        """Clean the URL by removing empty query parameters."""
        if url.endswith('?'):
            return url[:-1]
        return url
    
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).single().execute()
        
        if response.data and response.data.get('photo_url'):
            # Construct the full path including user folder
            user_folder = str(user_id)
            filename = response.data['photo_url'].split('/')[-1].split('?')[0]
            file_path = f"{user_folder}/{filename}"
            
            # Get fresh public URL with the full path
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
                # Extract filename only from the URL
                old_filename = existing_profile['photo_url'].split('/')[-1].split('?')[0]
                old_path = f"{user_folder}/{old_filename}"
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
            
            # Get public URL with the full path
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
                
            # Handle slug validation separately
            if profile_data.slug is not None:
                clean_slug = profile_data.slug.strip()
                
                # Check if slug is unchanged from the user's existing slug
                if existing_profile.get('slug') != clean_slug:
                    # Only check availability if the slug is different from current
                    slug_check = (
                        supabase.table("user_profiles")
                        .select("user_id")
                        .eq("slug", clean_slug)
                        .neq("user_id", user_id_int)  # Directly check for OTHER users
                        .execute()
                    )
                    
                    # If any other users have this slug, it's taken
                    if slug_check.data and len(slug_check.data) > 0:
                        raise HTTPException(status_code=400, detail="Slug is already taken")
                
                # If we reach here, the slug is either unchanged or available
                update_data['slug'] = clean_slug
                
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
                # Construct the full path including user folder
                user_folder = str(user_id_int)
                filename = updated_profile['photo_url'].split('/')[-1].split('?')[0]
                file_path = f"{user_folder}/{filename}"
                
                # Get fresh public URL with the full path
                updated_profile['photo_url'] = supabase.storage.from_('user_profile_photos').get_public_url(file_path)
            
            return updated_profile
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid user ID format: {str(e)}")
        except HTTPException:
            # Re-raise HTTP exceptions without modification
            raise
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
        
        # Check if slug is already taken by another user
        if profile_data.slug:
            slug_check = (
                supabase.table("user_profiles")
                .select("user_id")
                .eq("slug", profile_data.slug)
                .execute()
            )
            
            if slug_check.data and len(slug_check.data) > 0:
                raise HTTPException(status_code=400, detail="Slug is already taken")
        
        # Handle photo upload if provided
        photo_url = None
        if photo:
            photo_url = await UserProfileService._handle_photo_upload(user_id, photo)

        try:
            # Insert a new record, let the database handle the auto-incrementing id
            result = supabase.table("user_profiles").insert({
                "user_id": user_id,
                "display_name": profile_data.display_name,
                "slug": profile_data.slug,
                "photo_url": photo_url or profile_data.photo_url
            }, returning="*").execute()
            
            if result.data:
                # If we have a photo_url in the result, make sure it's fresh
                if result.data[0].get('photo_url') and not photo_url:
                    # Handle existing photo_url if it wasn't just uploaded
                    user_folder = str(user_id)
                    filename = result.data[0]['photo_url'].split('/')[-1].split('?')[0]
                    file_path = f"{user_folder}/{filename}"
                    result.data[0]['photo_url'] = supabase.storage.from_('user_profile_photos').get_public_url(file_path)
                
                return result.data[0]
            else:
                raise HTTPException(status_code=500, detail="Failed to create user profile")
        
        except Exception as e:
            print(f"Insertion error: {e}")
            raise
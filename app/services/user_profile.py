from app.db.session import get_supabase
from app.schemas.user.profile import UserProfileCreate, UserProfileUpdate
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
import uuid
import re

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
            user_folder = str(user_id)
            filename = response.data['photo_url'].split('/')[-1].split('?')[0]
            file_path = f"{user_folder}/{filename}"
            
            public_url = supabase.storage.from_("user_profile_photos").get_public_url(file_path)
            response.data['photo_url'] = public_url
            
        return response.data

    @staticmethod
    async def _handle_photo_upload(user_id: int, photo: UploadFile) -> str:
        try:
            contents = await photo.read()
            file_extension = photo.filename.split('.')[-1].lower()
            
            user_folder = str(user_id)
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            full_path = f"{user_folder}/{unique_filename}"
            
            supabase = get_supabase()
            
            existing_profile = await UserProfileService.get_by_user_id(user_id)
            if existing_profile and existing_profile.get('photo_url'):
                try:
                    old_url = existing_profile['photo_url']
                    old_filename = old_url.split('/')[-1]
                    
                    if '?' in old_filename:
                        old_filename = old_filename.split('?')[0]
                    
                    old_path = f"{user_folder}/{old_filename}"
                    print(f"Attempting to delete old photo at path: {old_path}")
                    
                    supabase.storage.from_('user_profile_photos').remove(old_path)
                    print(f"Successfully deleted old photo")
                except Exception as e:
                    print(f"Warning: Failed to delete old photo: {str(e)}")
            
            upload_response = supabase.storage.from_('user_profile_photos').upload(
                path=full_path,  
                file=contents,
                file_options={
                    "content-type": photo.content_type,
                    "cache-control": "3600"
                }
            )
            
            if hasattr(upload_response, 'error') and upload_response.error:
                raise Exception(f"Upload failed: {upload_response.error}")
            
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
            
            existing_profile = await UserProfileService.get_by_user_id(user_id_int)
            
            if not existing_profile:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            photo_url = None
            if photo:
                photo_url = await UserProfileService._handle_photo_upload(user_id_int, photo)
                
            update_data = {}
            if profile_data.display_name is not None:
                display_name = profile_data.display_name.strip()
                if len(display_name) > 30:
                    raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
                update_data['display_name'] = display_name
                
            if profile_data.slug is not None:
                clean_slug = profile_data.slug.strip().lower()
                
                if clean_slug:
                    # Check for spaces
                    if ' ' in clean_slug:
                        raise HTTPException(
                            status_code=400, 
                            detail="Slug cannot contain spaces"
                        )
                        
                    # Check character limit
                    if len(clean_slug) > 20:
                        raise HTTPException(
                            status_code=400, 
                            detail="Slug must be 20 characters or less"
                        )
                        
                    # Check valid characters
                    if not re.match(r'^[a-zA-Z0-9-]+$', clean_slug):
                        raise HTTPException(
                            status_code=400, 
                            detail="Slug can only contain letters, numbers, and hyphens"
                        )
                    
                    # Check if slug is unchanged from the user's existing slug
                    if existing_profile.get('slug') != clean_slug:
                        slug_check = supabase.table("user_profiles").select("user_id").eq("slug", clean_slug).execute()

                        if slug_check.data and any(item.get('user_id') != user_id_int for item in slug_check.data):
                            raise HTTPException(
                                status_code=400, 
                                detail="Slug is already taken. Please choose a different one."
                            )
                
                    update_data['slug'] = clean_slug
                    
            # Handle title field
            if profile_data.title is not None:
                title = profile_data.title.strip()
                if len(title) > 40:
                    raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
                update_data['title'] = title
                
            # Handle bio field
            if profile_data.bio is not None:
                bio = profile_data.bio.strip()
                if len(bio) > 200:
                    raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
                update_data['bio'] = bio

            if photo_url:
                update_data['photo_url'] = photo_url
            
            if not update_data:
                return existing_profile
            
            result = (
                supabase.table("user_profiles")
                .update(update_data)
                .eq("user_id", user_id_int)
                .execute()
            )
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            updated_profile = result.data[0]
            
            if updated_profile.get('photo_url'):
                user_folder = str(user_id_int)
                filename = updated_profile['photo_url'].split('/')[-1].split('?')[0]
                file_path = f"{user_folder}/{filename}"
                
                updated_profile['photo_url'] = supabase.storage.from_('user_profile_photos').get_public_url(file_path)
            
            return updated_profile
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid user ID format: {str(e)}")
        except HTTPException:
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
        
        # Validate display name
        if profile_data.display_name and len(profile_data.display_name.strip()) > 30:
            raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
            
        # Validate and clean slug
        if profile_data.slug:
            clean_slug = profile_data.slug.strip().lower()
            
            # Check for spaces
            if ' ' in clean_slug:
                raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
                
            # Check character limit
            if len(clean_slug) > 20:
                raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
                
            # Validate slug format
            if not re.match(r'^[a-zA-Z0-9-]+$', clean_slug):
                raise HTTPException(status_code=400, detail="Slug can only contain letters, numbers, and hyphens")
                
            profile_data.slug = clean_slug
        
        # Validate title
        if profile_data.title and len(profile_data.title.strip()) > 40:
            raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
        
        if profile_data.bio and len(profile_data.bio.strip()) > 200:
            raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
        
        photo_url = None
        if photo:
            photo_url = await UserProfileService._handle_photo_upload(user_id, photo)

        try:
            result = supabase.table("user_profiles").insert({
                "user_id": user_id,
                "display_name": profile_data.display_name.strip(),
                "slug": profile_data.slug,
                "photo_url": photo_url or profile_data.photo_url,
                "title": profile_data.title.strip() if profile_data.title else None,
                "bio": profile_data.bio.strip() if profile_data.bio else None
            }, returning="*").execute()
            
            if result.data:
                if result.data[0].get('photo_url') and not photo_url:
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
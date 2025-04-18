from app.db.session import get_supabase
from app.schemas.user.profile import UserProfileCreate, UserProfileUpdate
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
import uuid
import re
import qrcode
from io import BytesIO
import base64
import json

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
        
        # First check if response.data exists at all
        if not response.data:
            return None
        
        # Make a copy of the data to avoid modifying the original response
        profile_data = dict(response.data)
        
        # Handle photo URL if it exists
        if profile_data.get('photo_url'):
            user_folder = str(user_id)
            filename = profile_data['photo_url'].split('/')[-1].split('?')[0]
            file_path = f"{user_folder}/{filename}"
            
            public_url = supabase.storage.from_("user_profile_photos").get_public_url(file_path)
            profile_data['photo_url'] = public_url
        
        # Ensure id field exists
        if 'id' not in profile_data or profile_data['id'] is None:
            profile_data['id'] = user_id  # Using user_id as a fallback
        
        return profile_data

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
    async def update_profile(user_id: str, profile_data: UserProfileUpdate, photo: UploadFile = None, company_logo: UploadFile = None, current_user=None, base_url: str = None) -> Dict[str, Any]:
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
                
            company_logo_url = None
            if company_logo:
                company_logo_url = await UserProfileService._handle_logo_upload(user_id_int, company_logo)
                
            update_data = {}
            if profile_data.display_name is not None:
                display_name = profile_data.display_name.strip()
                if len(display_name) > 30:
                    raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
                update_data['display_name'] = display_name
            
            # Handle slug update separately from display_name
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
                    
                    # Always update QR code data when slug changes
                    if clean_slug != existing_profile.get('slug'):
                        # Default base URL if not provided
                        if not base_url:
                            base_url = "https://yourdomain.com/profile"
                        
                        update_data['qr_code_url'] = UserProfileService.generate_qr_code_url(clean_slug, base_url)
            
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

            # Handle new fields
            if profile_data.email is not None:
                # Email validation is handled by Pydantic
                update_data['email'] = profile_data.email
                
            if profile_data.website is not None:
                # URL validation is handled by Pydantic
                update_data['website'] = str(profile_data.website)
                
            if profile_data.contact is not None:
                update_data['contact'] = profile_data.contact
                
            # Handle explicit QR code data update
            if hasattr(profile_data, 'qr_code_url') and profile_data.qr_code_url is not None:
                update_data['qr_code_url'] = profile_data.qr_code_url

            if photo_url:
                update_data['photo_url'] = photo_url
                
            if company_logo_url:
                update_data['company_logo_url'] = company_logo_url
            
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
        photo: Optional[UploadFile] = None,
        company_logo: Optional[UploadFile] = None
    ) -> Dict[str, Any]:
        supabase = get_supabase()
        
        if profile_data.user_id != user_id:
            profile_data.user_id = user_id
        
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
            
        company_logo_url = None
        if company_logo:
            company_logo_url = await UserProfileService._handle_logo_upload(user_id, company_logo)

        # Generate QR code URL for the profile
        profile_url = UserProfileService.generate_qr_code_url(profile_data.slug)

        # Create the profile
        insert_data = {
            "user_id": user_id,
            "display_name": profile_data.display_name.strip() if profile_data.display_name else "",
            "slug": profile_data.slug,
            "photo_url": photo_url or profile_data.photo_url if hasattr(profile_data, 'photo_url') else None,
            "company_logo_url": company_logo_url or profile_data.company_logo_url if hasattr(profile_data, 'company_logo_url') else None,
            "title": profile_data.title.strip() if profile_data.title else None,
            "bio": profile_data.bio.strip() if profile_data.bio else None,
            "email": profile_data.email,
            "website": str(profile_data.website) if profile_data.website else None,
            "contact": profile_data.contact,
            "qr_code_url": profile_url  # Use the consistent field name for the database
        }
        
        # Debug info - print data being inserted
        print(f"Attempting to insert user profile with data: {json.dumps(insert_data, default=str)}")
        
        try:
            # First attempt the insert
            result = supabase.table("user_profiles").insert(insert_data, returning="*").execute()
            
            # Check if we have data in the response
            if hasattr(result, 'data') and result.data:
                profile_data = result.data[0]
            else:
                # If not, immediately fetch the profile we just created
                fetch_result = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
                
                if not fetch_result.data:
                    raise Exception("Failed to create or retrieve user profile")
                    
                profile_data = fetch_result.data[0]
            
            # Format photo URL if it exists
            if profile_data.get('photo_url') and not photo_url:
                user_folder = str(user_id)
                filename = profile_data['photo_url'].split('/')[-1].split('?')[0]
                file_path = f"{user_folder}/{filename}"
                profile_data['photo_url'] = supabase.storage.from_('user_profile_photos').get_public_url(file_path)
            
            # Format company logo URL if it exists
            if profile_data.get('company_logo_url') and not company_logo_url:
                user_folder = f"{user_id}/company_logos"
                filename = profile_data['company_logo_url'].split('/')[-1].split('?')[0]
                file_path = f"{user_folder}/{filename}"
                profile_data['company_logo_url'] = supabase.storage.from_('user_profile_photos').get_public_url(file_path)
            
            return profile_data
        
        except Exception as e:
            print(f"Error creating user profile: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Check if the profile was created despite the error
            try:
                existing_profile = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
                
                if existing_profile.data:
                    # If we found a profile, it means the creation succeeded but the response was empty
                    print("Profile was created but response was empty, returning existing profile")
                    return existing_profile.data[0]
                else:
                    # Clean up just in case
                    supabase.table("user_profiles").delete().eq("user_id", user_id).execute()
            except Exception as cleanup_error:
                print(f"Failed to check/clean up profile: {str(cleanup_error)}")
                    
            raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")

        
    @staticmethod
    async def _handle_logo_upload(user_id: int, logo: UploadFile) -> str:
        try:
            contents = await logo.read()
            file_extension = logo.filename.split('.')[-1].lower()
            
            # Create a subfolder for company logos
            user_folder = f"{user_id}/company_logos"
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            full_path = f"{user_folder}/{unique_filename}"
            
            supabase = get_supabase()
            
            existing_profile = await UserProfileService.get_by_user_id(user_id)
            if existing_profile and existing_profile.get('company_logo_url'):
                try:
                    old_url = existing_profile['company_logo_url']
                    old_filename = old_url.split('/')[-1]
                    
                    if '?' in old_filename:
                        old_filename = old_filename.split('?')[0]
                    
                    old_path = f"{user_folder}/{old_filename}"
                    print(f"Attempting to delete old company logo at path: {old_path}")
                    
                    supabase.storage.from_('user_profile_photos').remove(old_path)
                    print(f"Successfully deleted old company logo")
                except Exception as e:
                    print(f"Warning: Failed to delete old company logo: {str(e)}")
            
            # Ensure the folder exists
            try:
                supabase.storage.from_('user_profile_photos').list(user_folder)
            except Exception:
                # If folder doesn't exist, create it by uploading a placeholder
                placeholder_path = f"{user_folder}/.placeholder"
                supabase.storage.from_('user_profile_photos').upload(
                    path=placeholder_path,
                    file=b"",
                    file_options={"content-type": "application/octet-stream"}
                )
            
            upload_response = supabase.storage.from_('user_profile_photos').upload(
                path=full_path,  
                file=contents,
                file_options={
                    "content-type": logo.content_type,
                    "cache-control": "3600"
                }
            )
            
            if hasattr(upload_response, 'error') and upload_response.error:
                raise Exception(f"Upload failed: {upload_response.error}")
            
            public_url = supabase.storage.from_('user_profile_photos').get_public_url(full_path)
            
            print(f"Successfully uploaded company logo: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"Company logo upload error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Company logo upload failed: {str(e)}")
        
    @staticmethod
    def generate_qr_code_url(user_slug: str, base_url: Optional[str] = None) -> str:
        """Generate QR code data for a user's profile page"""
        # Default base URL if not provided
        if not base_url:
            base_url = "https://yourdomain.com/profile"
        
        # Create the URL for the user's profile
        profile_url = f"{base_url}/{user_slug}"
        
        return profile_url
        
    @staticmethod
    def generate_qr_code_image(data: str) -> str:
        """Generate QR code image and return as base64 string"""
        try:
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # Add data to QR code
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create an image from the QR Code
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save image to BytesIO buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Convert to base64
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            print(f"QR code generation error: {str(e)}")
            return None
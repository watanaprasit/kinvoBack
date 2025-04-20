# from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, Body
# from typing import Optional, Dict, Any
# from sqlalchemy.exc import IntegrityError
# from pydantic import EmailStr, HttpUrl
# from app.schemas.user.profile import UserProfile, UserProfileCreate, UserProfileUpdate
# from app.schemas.user.user import UserResponse
# from app.services.user import UserService
# from app.core.security import get_current_user
# from app.services.user_profile import UserProfileService
# import json

# router = APIRouter()

# @router.get("/by-email")
# async def get_user_by_email(email: str = Query(...)):
#     """
#     Get user data by email with their profile information
#     """
#     try:
#         user = await UserService.get_by_email(email)
        
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
        
#         profile = await UserProfileService.get_by_user_id(user["id"])
    
#         if not profile:
#             profile_data = UserProfileCreate(
#                 user_id=user["id"],
#                 display_name=user["full_name"],
#                 slug=user["slug"]
#             )
#             profile = await UserProfileService.create_profile(
#                 user_id=user["id"],
#                 profile_data=profile_data
#             )

#         return {
#             "id": user["id"],
#             "email": user["email"],
#             "full_name": user["full_name"],
#             "username": user.get("username"),
#             "slug": user["slug"],
#             "profile": profile
#         }
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         print(f"Error in get_user_by_email: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/me", response_model=UserResponse)
# async def get_current_user_data(current_user = Depends(get_current_user)):
#     try:
#         # Get user profile data
#         profile = await UserProfileService.get_by_user_id(current_user.id)
        
#         return {
#             "id": current_user.id,
#             "email": current_user.email,
#             "full_name": current_user.full_name,
#             "slug": current_user.slug,
#             "created_at": current_user.created_at,
#             "updated_at": current_user.updated_at,
#             "google_id": current_user.google_id,
#             "profile": profile  # Include profile data in response
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.put("/me/slug", response_model=UserResponse)
# async def update_user_slug(
#     slug: str,
#     current_user = Depends(get_current_user)
# ):
#     try:
#         # Validate slug
#         slug = slug.strip().lower()
        
#         if len(slug) > 20:
#             raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
            
#         if ' ' in slug:
#             raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
            
#         updated_user = await UserService.update_slug(current_user.id, slug)
#         if not updated_user:
#             raise HTTPException(status_code=404, detail="User not found")
        
#         # Get updated profile data
#         profile = await UserProfileService.get_by_user_id(current_user.id)
#         return {**updated_user, "profile": profile}
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except IntegrityError:
#         raise HTTPException(status_code=400, detail="Slug already taken")

# @router.get("/check-slug/{slug}")
# async def check_slug_availability(slug: str):
#     try:
#         # Validate slug format before checking availability
#         slug = slug.strip().lower()
        
#         if len(slug) > 20:
#             return {"available": False, "error": "Slug must be 20 characters or less"}
            
#         if ' ' in slug:
#             return {"available": False, "error": "Slug cannot contain spaces"}
            
#         is_available = await UserService.check_slug_availability(slug)
#         return {"available": is_available}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/{user_id}/profile", response_model=UserProfile)
# async def get_user_profile(user_id: int):
#     user_profile = await UserProfileService.get_by_user_id(user_id)
#     if not user_profile:
#         raise HTTPException(status_code=404, detail="User profile not found")
#     return user_profile


# @router.put("/me/profile", response_model=UserProfile)
# async def update_user_profile(
#     display_name: Optional[str] = Form(None),
#     slug: Optional[str] = Form(None),
#     title: Optional[str] = Form(None),
#     bio: Optional[str] = Form(None),
#     email: Optional[str] = Form(None),
#     website: Optional[str] = Form(None),
#     contact: Optional[str] = Form(None),
#     base_url: Optional[str] = Form(None),  # Add this parameter
#     photo: Optional[UploadFile] = File(None),
#     company_logo: Optional[UploadFile] = File(None),
#     current_user: UserResponse = Depends(get_current_user)
# ):
#     try:
#         # Validate inputs
#         if display_name is not None:
#             if not display_name.strip():
#                 raise HTTPException(status_code=400, detail="Display name cannot be empty")
#             if len(display_name.strip()) > 30:
#                 raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
        
#         # Validate slug
#         if slug is not None and slug.strip():
#             slug = slug.strip().lower()
            
#             if len(slug) > 20:
#                 raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
                
#             if ' ' in slug:
#                 raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
                
#             slug_available = await UserService.check_slug_availability(slug)
#             if not slug_available:
#                 raise HTTPException(status_code=400, detail="Slug is already taken")
                
#         # Validate title
#         if title is not None and len(title.strip()) > 40:
#             raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
        
#         if bio is not None and len(bio.strip()) > 200:
#             raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
            
#         # Parse contact JSON if provided
#         contact_data = None
#         if contact is not None:
#             try:
#                 contact_data = json.loads(contact)
#             except json.JSONDecodeError:
#                 raise HTTPException(status_code=400, detail="Invalid JSON format for contact field")
            
#         # Create profile update data with only the fields that are provided
#         profile_data = UserProfileUpdate(
#             display_name=display_name if display_name is not None else None,
#             slug=slug if slug is not None and slug.strip() else None,
#             title=title if title is not None else None,
#             bio=bio if bio is not None else None,
#             photo_url=None,
#             company_logo_url=None,
#             email=email,  # New field
#             website=website,  # New field
#             contact=contact_data  # New field
#         )
        
#         # Update profile first
#         updated_profile = await UserProfileService.update_profile(
#             user_id=str(current_user.id),
#             profile_data=profile_data,
#             photo=photo,
#             company_logo=company_logo,
#             current_user=current_user,
#             base_url=base_url  # Pass the base_url
#         )
        
#         # If profile update succeeds and slug is provided, update the slug
#         if slug is not None and slug.strip() and updated_profile:
#             await UserService.update_slug(current_user.id, slug)
        
#         return updated_profile
        
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to update profile: {str(e)}"
#         )

# @router.post("/profile", response_model=UserProfile)
# async def create_user_profile(
#     user_id: int = Form(...),
#     display_name: str = Form(...),
#     slug: str = Form(...),
#     title: Optional[str] = Form(None),
#     bio: Optional[str] = Form(None),
#     email: Optional[EmailStr] = Form(None),  # New field
#     website: Optional[str] = Form(None),  # New field
#     contact: Optional[str] = Form(None),  # New field as JSON string
#     photo: Optional[UploadFile] = File(None),
#     company_logo: Optional[UploadFile] = File(None)
# ):
#     try:
#         # Validate display_name
#         if len(display_name.strip()) > 30:
#             raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
            
#         # Process and validate slug
#         slug = slug.strip().lower() if slug else None
        
#         if not slug:
#             raise HTTPException(status_code=400, detail="Slug is required")
            
#         if len(slug) > 20:
#             raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
            
#         if ' ' in slug:
#             raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
        
#         # Validate title
#         if title and len(title.strip()) > 40:
#             raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
        
#         if bio and len(bio.strip()) > 200:
#             raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
        
#         # Parse contact JSON if provided
#         contact_data = None
#         if contact:
#             try:
#                 contact_data = json.loads(contact)
#             except json.JSONDecodeError:
#                 raise HTTPException(status_code=400, detail="Invalid JSON format for contact field")
        
#         profile_data = UserProfileCreate(
#             user_id=user_id,
#             display_name=display_name,
#             slug=slug,
#             title=title,
#             bio=bio,
#             email=email,  # New field
#             website=website,  # New field
#             contact=contact_data  # New field
#         )
        
#         user_profile = await UserProfileService.create_profile(
#             user_id=user_id,
#             profile_data=profile_data,
#             photo=photo,
#             company_logo=company_logo
#         )
        
#         if not user_profile:
#             raise HTTPException(status_code=500, detail="Failed to create user profile")
        
#         return user_profile
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.put("/me/display-name", response_model=UserProfile)
# async def update_display_name(
#     display_name: str = Form(...),
#     current_user: UserResponse = Depends(get_current_user)
# ):
#     try:
#         # Validate display name
#         if not display_name.strip():
#             raise HTTPException(status_code=400, detail="Display name cannot be empty")
            
#         if len(display_name.strip()) > 30:
#             raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
        
#         # Create profile update data with ONLY display_name
#         profile_data = UserProfileUpdate(
#             display_name=display_name,
#             slug=None,  # Explicitly set to None
#             photo_url=None,
#             title=None,
#             bio=None,
#             email=None,  # New field
#             website=None,  # New field
#             contact=None  # New field
#         )
        
#         # Update profile with only the display name
#         updated_profile = await UserProfileService.update_profile(
#             user_id=str(current_user.id),
#             profile_data=profile_data,
#             photo=None,
#             current_user=current_user
#         )
        
#         return updated_profile
        
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to update display name: {str(e)}"
#         )

# # Add new endpoints specifically for the new fields
# @router.put("/me/contact-info", response_model=UserProfile)
# async def update_contact_info(
#     email: Optional[EmailStr] = Form(None),
#     website: Optional[str] = Form(None),
#     contact: Optional[str] = Form(None),  # Expected as JSON string
#     current_user: UserResponse = Depends(get_current_user)
# ):
#     try:
#         # Validate website URL (Pydantic will handle email validation)
#         if website is not None:
#             # Simple URL validation
#             if not website.startswith(('http://', 'https://')):
#                 raise HTTPException(status_code=400, detail="Website must be a valid URL starting with http:// or https://")
        
#         # Parse contact JSON if provided
#         contact_data = None
#         if contact:
#             try:
#                 contact_data = json.loads(contact)
#                 if not isinstance(contact_data, dict):
#                     raise HTTPException(status_code=400, detail="Contact must be a valid JSON object")
#             except json.JSONDecodeError:
#                 raise HTTPException(status_code=400, detail="Invalid JSON format for contact field")
        
#         # Create profile update data with only contact-related fields
#         profile_data = UserProfileUpdate(
#             display_name=None,
#             slug=None,
#             photo_url=None,
#             company_logo_url=None,
#             title=None,
#             bio=None,
#             email=email,
#             website=website,
#             contact=contact_data
#         )
        
#         # Update profile with only the contact info
#         updated_profile = await UserProfileService.update_profile(
#             user_id=str(current_user.id),
#             profile_data=profile_data,
#             photo=None,
#             company_logo=None,
#             current_user=current_user
#         )
        
#         return updated_profile
        
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to update contact information: {str(e)}"
#         )
        
        
# @router.get("/{slug}", response_model=UserResponse)
# async def get_user_by_slug(slug: str):
#     # This existing endpoint handles '/profile/{slug}'
#     try:
#         user = await UserService.get_by_slug(slug)
        
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
        
#         # Get user profile data
#         profile = await UserProfileService.get_by_user_id(user["id"])
        
#         return {
#             "id": user["id"],
#             "email": user["email"],
#             "full_name": user["full_name"],
#             "slug": user["slug"],
#             "created_at": user["created_at"],
#             "updated_at": user["updated_at"],
#             "google_id": None,
#             "profile": profile
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/me/qrcode", response_model=Dict[str, str])
# async def get_qr_code(
#     base_url: Optional[str] = Query(None),
#     current_user: UserResponse = Depends(get_current_user)
# ):
#     try:
#         # Get user profile
#         user_profile = await UserProfileService.get_by_user_id(current_user.id)
        
#         if not user_profile:
#             raise HTTPException(status_code=404, detail="Profile not found")
        
#         # Get QR code data
#         qr_data = user_profile.get('qr_code_url')
        
#         # If no QR code data exists, generate it
#         if not qr_data:
#             qr_data = UserProfileService.generate_qr_code_url(user_profile['slug'], base_url)
            
#             # Update the profile with the new QR code data
#             update_data = UserProfileUpdate(qr_code_url=qr_data)
#             await UserProfileService.update_profile(
#                 user_id=str(current_user.id),
#                 profile_data=update_data,
#                 current_user=current_user
#             )
        
#         # Generate QR code image
#         qr_image = UserProfileService.generate_qr_code_image(qr_data)
        
#         return {
#             "qr_data": qr_data,
#             "qr_image": qr_image
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")

# @router.put("/me/qrcode", response_model=Dict[str, str])
# async def update_qr_code(
#     qr_data: str = Body(..., embed=True),
#     current_user: UserResponse = Depends(get_current_user)
# ):
#     try:
#         # Get user profile
#         user_profile = await UserProfileService.get_by_user_id(current_user.id)
        
#         if not user_profile:
#             raise HTTPException(status_code=404, detail="Profile not found")
        
#         # Update profile with custom QR code data
#         update_data = UserProfileUpdate(qr_code_url=qr_data)
#         updated_profile = await UserProfileService.update_profile(
#             user_id=str(current_user.id),
#             profile_data=update_data,
#             current_user=current_user
#         )
        
#         # Generate QR code image
#         qr_image = UserProfileService.generate_qr_code_image(qr_data)
        
#         return {
#             "qr_data": qr_data,
#             "qr_image": qr_image
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to update QR code: {str(e)}")
    
# @router.get("/{slug}/qrcode", response_model=Dict[str, str])
# async def get_public_qr_code(
#     slug: str,
#     base_url: Optional[str] = Query(None)
# ):
#     try:
#         # Get user by slug
#         user = await UserService.get_by_slug(slug)
        
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
        
#         # Get user profile
#         user_profile = await UserProfileService.get_by_user_id(user["id"])
        
#         if not user_profile:
#             raise HTTPException(status_code=404, detail="Profile not found")
        
#         # Get QR code data
#         qr_data = user_profile.get('qr_code_url')
        
#         # If no QR code data exists, generate it
#         if not qr_data:
#             qr_data = UserProfileService.generate_qr_code_url(user_profile['slug'], base_url)
        
#         # Generate QR code image
#         qr_image = UserProfileService.generate_qr_code_image(qr_data)
        
#         return {
#             "qr_data": qr_data,
#             "qr_image": qr_image
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")
    
    
# new below

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, Body
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import IntegrityError
from pydantic import EmailStr, HttpUrl
from app.schemas.user.business_card import BusinessCard, BusinessCardCreate, BusinessCardUpdate
from app.schemas.user.user import UserResponse
from app.services.user import UserService
from app.core.security import get_current_user
from app.services.business_card import BusinessCardService
import json

router = APIRouter()

@router.get("/by-email")
async def get_user_by_email(email: str = Query(...)):
    """
    Get user data by email with their primary business card information
    """
    try:
        user = await UserService.get_by_email(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        business_card = await BusinessCardService.get_primary_by_user_id(user["id"])
    
        if not business_card:
            card_data = BusinessCardCreate(
                user_id=user["id"],
                display_name=user["full_name"],
                slug=user["slug"],
                is_primary=True
            )
            business_card = await BusinessCardService.create_business_card(
                user_id=user["id"],
                card_data=card_data
            )

        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "username": user.get("username"),
            "slug": user["slug"],
            "business_card": business_card
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in get_user_by_email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_data(current_user = Depends(get_current_user)):
    try:
        # Get user's primary business card
        business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "slug": current_user.slug,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "google_id": current_user.google_id,
            "business_card": business_card  # Include business card data in response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/me/slug", response_model=UserResponse)
async def update_user_slug(
    slug: str,
    current_user = Depends(get_current_user)
):
    try:
        # Validate slug
        slug = slug.strip().lower()
        
        if len(slug) > 20:
            raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
            
        if ' ' in slug:
            raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
            
        updated_user = await UserService.update_slug(current_user.id, slug)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get updated business card data
        business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        return {**updated_user, "business_card": business_card}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Slug already taken")

@router.get("/check-slug/{slug}")
async def check_slug_availability(slug: str):
    try:
        # Validate slug format before checking availability
        slug = slug.strip().lower()
        
        if len(slug) > 20:
            return {"available": False, "error": "Slug must be 20 characters or less"}
            
        if ' ' in slug:
            return {"available": False, "error": "Slug cannot contain spaces"}
            
        is_available = await UserService.check_slug_availability(slug)
        return {"available": is_available}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/business-cards", response_model=List[BusinessCard])
async def get_user_business_cards(
    user_id: int,
    current_user = Depends(get_current_user)
):
    # Only allow users to access their own business cards
    if str(current_user.id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")
    
    business_cards = await BusinessCardService.get_by_user_id(user_id)
    return business_cards

@router.get("/{user_id}/business-card", response_model=BusinessCard)
async def get_user_primary_business_card(user_id: int):
    business_card = await BusinessCardService.get_primary_by_user_id(user_id)
    if not business_card:
        raise HTTPException(status_code=404, detail="Business card not found")
    return business_card

@router.post("/business-card", response_model=BusinessCard)
async def create_business_card(
    display_name: str = Form(...),
    slug: str = Form(...),
    title: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    email: Optional[EmailStr] = Form(None),
    website: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    photo: Optional[UploadFile] = File(None),
    company_logo: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user)
):
    try:
        # Check if user can create more business cards
        can_create = await UserService.can_create_business_card(current_user.id)
        if not can_create:
            subscription_tier = await UserService.get_subscription_tier(current_user.id)
            raise HTTPException(
                status_code=403, 
                detail=f"You've reached the maximum number of business cards for your {subscription_tier} subscription"
            )
        
        # Validate display_name
        if len(display_name.strip()) > 30:
            raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
            
        # Process and validate slug
        slug = slug.strip().lower() if slug else None
        
        if not slug:
            raise HTTPException(status_code=400, detail="Slug is required")
            
        if len(slug) > 20:
            raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
            
        if ' ' in slug:
            raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
        
        # Validate title
        if title and len(title.strip()) > 40:
            raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
        
        if bio and len(bio.strip()) > 200:
            raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
        
        # Parse contact JSON if provided
        contact_data = None
        if contact:
            try:
                contact_data = json.loads(contact)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for contact field")
        
        card_data = BusinessCardCreate(
            user_id=current_user.id,
            display_name=display_name,
            slug=slug,
            title=title,
            bio=bio,
            email=email,
            website=website,
            contact=contact_data,
            is_primary=is_primary
        )
        
        business_card = await BusinessCardService.create_business_card(
            user_id=current_user.id,
            card_data=card_data,
            photo=photo,
            company_logo=company_logo
        )
        
        if not business_card:
            raise HTTPException(status_code=500, detail="Failed to create business card")
        
        return business_card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/business-card/{card_id}", response_model=BusinessCard)
async def update_business_card(
    card_id: int,
    display_name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    is_primary: Optional[bool] = Form(None),
    base_url: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    company_logo: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user)
):
    try:
        # Verify card belongs to user
        card = await BusinessCardService.get_by_id(card_id)
        if not card or card.get('user_id') != current_user.id:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Validate inputs
        if display_name is not None:
            if not display_name.strip():
                raise HTTPException(status_code=400, detail="Display name cannot be empty")
            if len(display_name.strip()) > 30:
                raise HTTPException(status_code=400, detail="Display name must be 30 characters or less")
        
        # Validate slug
        if slug is not None and slug.strip():
            slug = slug.strip().lower()
            
            if len(slug) > 20:
                raise HTTPException(status_code=400, detail="Slug must be 20 characters or less")
                
            if ' ' in slug:
                raise HTTPException(status_code=400, detail="Slug cannot contain spaces")
                
            # Check slug availability (unless it's the same as current)
            if slug != card.get('slug'):
                slug_available = await UserService.check_slug_availability(slug)
                if not slug_available:
                    raise HTTPException(status_code=400, detail="Slug is already taken")
                
        # Validate title
        if title is not None and len(title.strip()) > 40:
            raise HTTPException(status_code=400, detail="Title must be 40 characters or less")
        
        if bio is not None and len(bio.strip()) > 200:
            raise HTTPException(status_code=400, detail="Bio must be 200 characters or less")
            
        # Parse contact JSON if provided
        contact_data = None
        if contact is not None:
            try:
                contact_data = json.loads(contact)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for contact field")
            
        # Create card update data with only the fields that are provided
        card_data = BusinessCardUpdate(
            display_name=display_name if display_name is not None else None,
            slug=slug if slug is not None and slug.strip() else None,
            title=title if title is not None else None,
            bio=bio if bio is not None else None,
            photo_url=None,
            company_logo_url=None,
            email=email,
            website=website,
            contact=contact_data,
            is_primary=is_primary
        )
        
        # Update business card
        updated_card = await BusinessCardService.update_business_card(
            card_id=card_id,
            card_data=card_data,
            photo=photo,
            company_logo=company_logo,
            current_user=current_user,
            base_url=base_url
        )
        
        return updated_card
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update business card: {str(e)}"
        )

@router.delete("/business-card/{card_id}")
async def delete_business_card(
    card_id: int,
    current_user = Depends(get_current_user)
):
    try:
        # Verify card belongs to user
        card = await BusinessCardService.get_by_id(card_id)
        if not card or card.get('user_id') != current_user.id:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Don't allow deletion of primary card if it's the only card
        if card.get('is_primary'):
            all_cards = await BusinessCardService.get_by_user_id(current_user.id)
            if len(all_cards) <= 1:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete your only business card. Create another card before deleting this one."
                )
        
        success = await BusinessCardService.delete_business_card(card_id)
        if success:
            return {"message": "Business card deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete business card")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/business-card/{card_id}/set-primary", response_model=BusinessCard)
async def set_primary_business_card(
    card_id: int,
    current_user = Depends(get_current_user)
):
    try:
        # Verify card belongs to user
        card = await BusinessCardService.get_by_id(card_id)
        if not card or card.get('user_id') != current_user.id:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Set as primary
        updated_card = await BusinessCardService.set_as_primary(card_id, current_user.id)
        return updated_card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{slug}", response_model=UserResponse)
async def get_user_by_slug(slug: str):
    try:
        user = await UserService.get_by_slug(slug)
        
        if not user:
            # Check if the slug belongs to a business card
            business_card = await BusinessCardService.get_by_slug(slug)
            if not business_card:
                raise HTTPException(status_code=404, detail="User not found")
                
            # Get the user associated with this business card
            user = await UserService.get_user_by_id(business_card["user_id"])
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
                
            return {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "slug": user["slug"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"],
                "google_id": None,
                "business_card": business_card
            }
        
        # Get user's primary business card
        business_card = await BusinessCardService.get_primary_by_user_id(user["id"])
        
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "slug": user["slug"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "google_id": None,
            "business_card": business_card
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/business-card/{slug}", response_model=BusinessCard)
async def get_business_card_by_slug(slug: str):
    business_card = await BusinessCardService.get_by_slug(slug)
    if not business_card:
        raise HTTPException(status_code=404, detail="Business card not found")
    return business_card

@router.get("/me/qrcode", response_model=Dict[str, str])
async def get_qr_code(
    base_url: Optional[str] = Query(None),
    card_id: Optional[int] = Query(None),
    current_user = Depends(get_current_user)
):
    try:
        if card_id:
            # Get specific business card
            business_card = await BusinessCardService.get_by_id(card_id)
            if not business_card or business_card.get('user_id') != current_user.id:
                raise HTTPException(status_code=404, detail="Business card not found")
        else:
            # Get user's primary business card
            business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        
        if not business_card:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Get QR code data
        qr_data = business_card.get('qr_code_url')
        
        # If no QR code data exists, generate it
        if not qr_data:
            qr_data = BusinessCardService.generate_qr_code_url(business_card['slug'], base_url)
            
            # Update the business card with the new QR code data
            update_data = BusinessCardUpdate(qr_code_url=qr_data)
            if card_id:
                await BusinessCardService.update_business_card(
                    card_id=card_id,
                    card_data=update_data,
                    current_user=current_user
                )
            else:
                await BusinessCardService.update_business_card(
                    card_id=business_card['id'],
                    card_data=update_data,
                    current_user=current_user
                )
        
        # Generate QR code image
        qr_image = BusinessCardService.generate_qr_code_image(qr_data)
        
        return {
            "qr_data": qr_data,
            "qr_image": qr_image
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")

@router.put("/me/qrcode", response_model=Dict[str, str])
async def update_qr_code(
    qr_data: str = Body(..., embed=True),
    card_id: Optional[int] = Body(None),
    current_user = Depends(get_current_user)
):
    try:
        if card_id:
            # Get specific business card
            business_card = await BusinessCardService.get_by_id(card_id)
            if not business_card or business_card.get('user_id') != current_user.id:
                raise HTTPException(status_code=404, detail="Business card not found")
        else:
            # Get user's primary business card
            business_card = await BusinessCardService.get_primary_by_user_id(current_user.id)
        
        if not business_card:
            raise HTTPException(status_code=404, detail="Business card not found")
        
        # Update business card with custom QR code data
        update_data = BusinessCardUpdate(qr_code_url=qr_data)
        
        if card_id:
            await BusinessCardService.update_business_card(
                card_id=card_id,
                card_data=update_data,
                current_user=current_user
            )
        else:
            await BusinessCardService.update_business_card(
                card_id=business_card['id'],
                card_data=update_data,
                current_user=current_user
            )
        
        # Generate QR code image
        qr_image = BusinessCardService.generate_qr_code_image(qr_data)
        
        return {
            "qr_data": qr_data,
            "qr_image": qr_image
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update QR code: {str(e)}")
    
@router.get("/{slug}/qrcode", response_model=Dict[str, str])
async def get_public_qr_code(
    slug: str,
    base_url: Optional[str] = Query(None)
):
    try:
        # Try to find business card by slug
        business_card = await BusinessCardService.get_by_slug(slug)
        
        if not business_card:
            # If no direct match, try to find user and their primary card
            user = await UserService.get_by_slug(slug)
            if not user:
                raise HTTPException(status_code=404, detail="User or business card not found")
            
            business_card = await BusinessCardService.get_primary_by_user_id(user["id"])
            if not business_card:
                raise HTTPException(status_code=404, detail="Business card not found")
        
        # Get QR code data
        qr_data = business_card.get('qr_code_url')
        
        # If no QR code data exists, generate it
        if not qr_data:
            qr_data = BusinessCardService.generate_qr_code_url(business_card['slug'], base_url)
        
        # Generate QR code image
        qr_image = BusinessCardService.generate_qr_code_image(qr_data)
        
        return {
            "qr_data": qr_data,
            "qr_image": qr_image
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")
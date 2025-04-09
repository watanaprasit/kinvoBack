from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query
from typing import Optional
from sqlalchemy.exc import IntegrityError
from app.schemas.user.profile import UserProfile, UserProfileCreate, UserProfileUpdate
from app.schemas.user.user import UserResponse
from app.services.user import UserService
from app.core.security import get_current_user
from app.services.user_profile import UserProfileService

router = APIRouter()

@router.get("/by-email")
async def get_user_by_email(email: str = Query(...)):
    """
    Get user data by email with their profile information
    """
    try:
        user = await UserService.get_by_email(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = await UserProfileService.get_by_user_id(user["id"])
    
        if not profile:
            profile_data = UserProfileCreate(
                user_id=user["id"],
                display_name=user["full_name"],
                slug=user["slug"]
            )
            profile = await UserProfileService.create_profile(
                user_id=user["id"],
                profile_data=profile_data
            )

        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "username": user.get("username"),
            "slug": user["slug"],
            "profile": profile
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in get_user_by_email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{slug}", response_model=UserResponse)
async def get_user_by_slug(slug: str):
    try:
        user = await UserService.get_by_slug(slug)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user profile data
        profile = await UserProfileService.get_by_user_id(user["id"])
        
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "slug": user["slug"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "google_id": None,
            "profile": profile  # Include profile data in response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_current_user_data(current_user = Depends(get_current_user)):
    try:
        # Get user profile data
        profile = await UserProfileService.get_by_user_id(current_user.id)
        
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "slug": current_user.slug,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "google_id": current_user.google_id,
            "profile": profile  # Include profile data in response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/me/slug", response_model=UserResponse)
async def update_user_slug(
    slug: str,
    current_user = Depends(get_current_user)
):
    try:
        updated_user = await UserService.update_slug(current_user.id, slug)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get updated profile data
        profile = await UserProfileService.get_by_user_id(current_user.id)
        return {**updated_user, "profile": profile}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Slug already taken")

@router.get("/check-slug/{slug}")
async def check_slug_availability(slug: str):
    try:
        is_available = await UserService.check_slug_availability(slug)
        return {"available": is_available}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(user_id: int):
    user_profile = await UserProfileService.get_by_user_id(user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user_profile


@router.put("/me/profile", response_model=UserProfile)
async def update_user_profile(
    display_name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: UserResponse = Depends(get_current_user)
):
    try:
        # Validate inputs
        if display_name is not None and not display_name.strip():
            raise HTTPException(status_code=400, detail="Display name cannot be empty")
        
        # Only check slug availability if slug is provided and not empty
        if slug is not None and slug.strip():
            slug_available = await UserService.check_slug_availability(slug)
            if not slug_available:
                raise HTTPException(status_code=400, detail="Slug is already taken")
            
        # Create profile update data with only the fields that are provided
        profile_data = UserProfileUpdate(
            display_name=display_name if display_name is not None else None,
            slug=slug if slug is not None and slug.strip() else None,
            photo_url=None
        )
        
        # Update profile first
        updated_profile = await UserProfileService.update_profile(
            user_id=str(current_user.id),
            profile_data=profile_data,
            photo=photo,
            current_user=current_user
        )
        
        # If profile update succeeds and slug is provided, update the slug
        if slug is not None and slug.strip() and updated_profile:
            await UserService.update_slug(current_user.id, slug)
        
        return updated_profile
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update profile: {str(e)}"
        )

@router.post("/profile", response_model=UserProfile)
async def create_user_profile(
    user_id: int = Form(...),
    display_name: str = Form(...),
    slug: str = Form(...),
    photo: Optional[UploadFile] = File(None)
):
    try:
        profile_data = UserProfileCreate(
            user_id=user_id,
            display_name=display_name,
            slug=slug
        )
        
        user_profile = await UserProfileService.create_profile(
            user_id=user_id,
            profile_data=profile_data,
            photo=photo
        )
        
        if not user_profile:
            raise HTTPException(status_code=500, detail="Failed to create user profile")
        
        return user_profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add this to your FastAPI router file

@router.put("/me/display-name", response_model=UserProfile)
async def update_display_name(
    display_name: str = Form(...),
    current_user: UserResponse = Depends(get_current_user)
):
    try:
        # Create profile update data with ONLY display_name
        profile_data = UserProfileUpdate(
            display_name=display_name,
            slug=None,  # Explicitly set to None
            photo_url=None
        )
        
        # Update profile with only the display name
        updated_profile = await UserProfileService.update_profile(
            user_id=str(current_user.id),
            profile_data=profile_data,
            photo=None,
            current_user=current_user
        )
        
        return updated_profile
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update display name: {str(e)}"
        )

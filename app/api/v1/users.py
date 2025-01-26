from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy.exc import IntegrityError
# from app.schemas.user.user import UserResponse, UserProfile, UserProfileCreate, UserProfileUpdate
from app.schemas.user.profile import UserProfile, UserProfileCreate, UserProfileUpdate
from app.schemas.user.user import UserResponse
from app.services.user import UserService
from app.core.security import get_current_user
from app.services.user_profile import UserProfileService

router = APIRouter()

@router.get("/{slug}", response_model=UserResponse)
async def get_user_by_slug(slug: str):
    try:
        user = await UserService.get_by_slug(slug)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "slug": user["slug"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "google_id": None  # Since this is in your schema but not in DB
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
        return updated_user
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

# With token request
# @router.get("/me/profile", response_model=UserProfile)
# async def get_user_profile(current_user=Depends(get_current_user)):
#     user_profile = await UserProfileService.get_by_user_id(str(current_user.id))
#     if not user_profile:
#         raise HTTPException(status_code=404, detail="User profile not found")
#     return user_profile

@router.put("/me/profile", response_model=UserProfile)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    photo: UploadFile = File(None),
    current_user=Depends(get_current_user)
):
    user_profile = await UserProfileService.update_profile(
        user_id=str(current_user.id),
        profile_data=profile_data,
        photo=photo
    )
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user_profile


@router.post("/profile", response_model=UserProfile)
async def create_user_profile(profile_data: UserProfileCreate):
    try:
        user_profile = await UserProfileService.create_profile(
            user_id=profile_data.user_id,  # Pass user_id from the input data
            profile_data=profile_data,
            profile_id=profile_data.id  # Optional: pass ID if provided
        )
        
        if not user_profile:
            raise HTTPException(status_code=500, detail="Failed to create user profile")
        
        return user_profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# with authentication
# @router.post("/me/profile", response_model=UserProfile)
# async def create_user_profile(
#     profile_data: UserProfileCreate,
#     current_user = Depends(get_current_user)
# ):
#     user = UserService.get_user_by_id(current_user.id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     user_profile = await UserProfileService.create_profile(
#         user_id=str(current_user.id),
#         profile_data=profile_data
#     )
    
#     if not user_profile:
#         raise HTTPException(status_code=500, detail="Failed to create user profile")
    
#     return user_profile


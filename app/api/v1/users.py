from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.exc import IntegrityError
from app.schemas.user import UserCreate, UserResponse
from app.services.user import UserService
from app.core.security import get_current_user
from typing import Optional
from app.db.session import get_supabase

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
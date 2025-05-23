from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, Union, Dict, Any, List
from datetime import datetime
from .base import BaseSlugModel

class BusinessCardBase(BaseSlugModel):
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    contact: Optional[Dict[str, Any]] = None
    qr_code_url: Optional[str] = None
    is_primary: Optional[bool] = False

class BusinessCardCreate(BaseModel):
    user_id: int
    display_name: str
    slug: str
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    contact: Optional[Dict[str, Any]] = None
    qr_code_url: Optional[str] = None
    is_primary: Optional[bool] = False

class BusinessCardUpdate(BaseModel):
    display_name: Optional[str] = None
    slug: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    contact: Optional[Dict[str, Any]] = None
    qr_code_url: Optional[str] = None
    is_primary: Optional[bool] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "display_name": "New Display Name",
                "slug": "new-slug",
                "photo_url": "https://example.com/photo.jpg",
                "company_logo_url": "https://example.com/company_logo.png",
                "title": "Software Developer",
                "bio": "I'm a passionate developer with over 5 years of experience.",
                "email": "user@example.com",
                "website": "https://example.com",
                "contact": {
                    "twitter": "@username",
                    "linkedin": "linkedin/username",
                    "phone": "+1234567890"
                },
                "qr_code_url": "https://example.com/user/new-slug",
                "is_primary": True
            }
        }
    }

class BusinessCard(BaseModel):
    id: Optional[int] = None
    user_id: int
    display_name: str
    slug: str
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    contact: Optional[Dict[str, Any]] = None
    qr_code_url: Optional[str] = None
    is_primary: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Keep these for backwards compatibility during migration
UserProfileBase = BusinessCardBase
UserProfileCreate = BusinessCardCreate
UserProfileUpdate = BusinessCardUpdate
UserProfile = BusinessCard
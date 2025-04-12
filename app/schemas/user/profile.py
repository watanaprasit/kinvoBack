from pydantic import BaseModel, Field
from typing import Optional, Union
from datetime import datetime
from .base import BaseSlugModel

class UserProfileBase(BaseSlugModel):
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None  # New field
    title: Optional[str] = None
    bio: Optional[str] = None

class UserProfileCreate(BaseModel):
    user_id: int
    display_name: str
    slug: str
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None  # New field
    title: Optional[str] = None
    bio: Optional[str] = None

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    slug: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None  # New field
    title: Optional[str] = None
    bio: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "display_name": "New Display Name",
                "slug": "new-slug",
                "photo_url": "https://example.com/photo.jpg",
                "company_logo_url": "https://example.com/company_logo.png",  # Add example
                "title": "Software Developer",
                "bio": "I'm a passionate developer with over 5 years of experience."
            }
        }
    }

class UserProfile(BaseModel):
    id: int
    user_id: int
    display_name: str
    slug: str
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None  # New field
    title: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
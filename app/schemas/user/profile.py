from pydantic import BaseModel, Field
from typing import Optional, Union
from datetime import datetime
from uuid import UUID
from .base import BaseSlugModel

class UserProfileBase(BaseSlugModel):
    display_name: Optional[str] = None
    photo_url: Optional[str] = None

class UserProfileCreate(BaseModel):
    user_id: int
    display_name: str
    slug: str
    photo_url: Optional[str] = None

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    slug: Optional[str] = None
    photo_url: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "display_name": "New Display Name",
                "slug": "new-slug",
                "photo_url": "https://example.com/photo.jpg"
            }
        }
    }

class UserProfile(BaseModel):
    id: int
    user_id: int
    display_name: str
    slug: str
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
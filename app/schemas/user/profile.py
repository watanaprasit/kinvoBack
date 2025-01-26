from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime
from uuid import UUID
from .base import BaseSlugModel

class UserProfileBase(BaseSlugModel):
    display_name: Optional[str] = None
    photo_url: Optional[str] = None

class UserProfileCreate(BaseModel):
    id: Optional[int] = None
    user_id: int
    display_name: str
    slug: str
    photo_url: Optional[str] = None

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    id: Union[int, str, UUID]
    user_id: Union[int, str, UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
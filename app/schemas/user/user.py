from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from .base import BaseSlugModel

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    slug: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleOAuthLogin(BaseModel):
    id_token: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    slug: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    slug: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    google_id: Optional[str] = None

    class Config:
        from_attributes = True
        
        
class UserPublicProfileResponse(BaseModel):
    display_name: str
    slug: str
    title: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    website: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None
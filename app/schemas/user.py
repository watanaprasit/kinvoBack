from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    slug: Optional[constr(min_length=3, max_length=50, pattern=r'^[a-z0-9-]+$')] = None

class UserCreate(UserBase):
    password: str  # For regular user registration

class UserLogin(BaseModel):
    email: EmailStr
    password: str  # For traditional login

class GoogleOAuthLogin(BaseModel):
    id_token: str  # The id_token you get from Google OAuth

class Token(BaseModel):
    access_token: str
    token_type: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    slug: Optional[constr(min_length=3, max_length=50, pattern=r'^[a-z0-9-]+$')] = None

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

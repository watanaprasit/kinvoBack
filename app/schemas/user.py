from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

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

class UserResponse(UserBase):
    id: int
    google_id: Optional[str] = None  # Google user ID (if using Google OAuth)

    class Config:
        from_attributes = True

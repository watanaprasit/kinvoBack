from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from supabase import create_client, Client
from ...schemas.user.user import UserCreate, UserLogin, UserResponse, GoogleOAuthLogin
from ...schemas.user.base import Token
from ...services.auth import AuthService, validate_google_oauth_token
from ...core.config import settings
from ...core.security import create_access_token, get_password_hash, verify_password
from ...services.user import UserService
import httpx
from pydantic import BaseModel
import random
import string
from datetime import datetime
from typing import Optional


class GoogleTokenRequest(BaseModel):
    id_token: str
    slug: Optional[str] = None
    is_login: Optional[bool] = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "slug": "user-slug",
                "is_login": False
            }
        }

router = APIRouter()
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def validate_google_oauth_token(id_token: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={id_token}")
            response_data = response.json()

            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Google token validation failed: {response_data.get('error_description', 'Unknown error')}")

            return response_data
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Token validation failed: {str(e)}")

def generate_random_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@router.post("/google/callback")
async def google_callback(token_request: GoogleTokenRequest):
    try:
        # Validate the ID token and get user info from Google
        user_data = await validate_google_oauth_token(token_request.id_token)
        
        # Handle the authentication through the service
        result = await AuthService.handle_google_auth(
            token_data=user_data,
            is_login=token_request.is_login,
            slug=token_request.slug
        )
        
        return result

    except HTTPException as http_error:
        return JSONResponse(
            status_code=http_error.status_code,
            content={
                "success": False,
                "error": {
                    "code": getattr(http_error.detail, "code", "UNKNOWN_ERROR"),
                    "message": str(http_error.detail)
                    if isinstance(http_error.detail, str)
                    else http_error.detail.get("message", str(http_error.detail))
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    try:
        # Check if the email already exists in Supabase
        users_response = supabase.auth.admin.list_users()

        if not isinstance(users_response, list):
            raise HTTPException(status_code=500, detail="Unable to fetch users from Supabase Auth")

        existing_user = next((u for u in users_response if u.user_metadata.get('email') == user.email), None)

        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if slug is already taken
        if user.slug:
            slug_check = supabase.table("users").select("id").eq("slug", user.slug).execute()
            if slug_check.data:
                raise HTTPException(status_code=400, detail="Slug already taken")

        # Register the user in Supabase Auth using correct method
        auth_user = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })

        if not auth_user.user:
            raise HTTPException(status_code=400, detail="Error creating user in Supabase Auth")

        # Hash the password and store user data in the custom table
        hashed_password = get_password_hash(user.password)
        current_time = datetime.utcnow().isoformat()
        new_user = {
            "email": user.email,
            "full_name": user.full_name,
            "hashed_password": hashed_password,
            "slug": user.slug,
            "created_at": current_time,
            "updated_at": current_time
        }

        # Insert the user into Supabase table
        result = supabase.table("users").insert(new_user).execute()

        if result.data and isinstance(result.data, list):
            return result.data[0]
        else:
            raise HTTPException(status_code=400, detail="Error inserting user into custom users table")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    try:
        result = supabase.table("users").select("*").eq("email", user_credentials.email).execute()

        if not result.data:
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        user = result.data[0]
        if not verify_password(user_credentials.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        access_token = create_access_token(data={"sub": user["email"]})

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from supabase import create_client, Client
from ...schemas.user import UserCreate, UserLogin, Token, UserResponse
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "slug": "user-slug"
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
        # Add detailed logging
        print("=== Debug Info ===")
        print(f"Token Request: {token_request}")
        
        # Validate the ID token and get user info from Google
        user_data = await validate_google_oauth_token(token_request.id_token)
        print(f"Validated Google User Data: {user_data}")

        if not user_data.get("email"):
            raise HTTPException(
                status_code=422, 
                detail={"message": "Email not found in token", "code": "INVALID_TOKEN"}
            )

        # Check if user already exists
        existing_user = supabase.table("users").select("*").eq("email", user_data["email"]).execute()
        
        if existing_user.data:
            raise HTTPException(
                status_code=422,
                detail={"message": "User already exists", "code": "USER_EXISTS"}
            )

        # If no slug provided, just validate and return user info
        if not token_request.slug:
            return {
                "email": user_data["email"],
                "name": user_data.get("name", ""),
                "success": True,
                "idToken": token_request.id_token  # Return the token for the second step
            }

        # If we have a slug, proceed with user creation
        random_password = generate_random_password()
        
        # Create user in Supabase Auth
        auth_user = supabase.auth.sign_up({
            "email": user_data["email"],
            "password": random_password,
            "options": {
                "data": {
                    "full_name": user_data.get("name", ""),
                    "google_id": user_data.get("sub")
                }
            }
        })

        if not auth_user.user:
            raise HTTPException(status_code=400, detail="Error creating user in Supabase Auth")

        # Create user in custom table
        current_time = datetime.utcnow().isoformat()
        new_user = {
            "email": user_data["email"],
            "full_name": user_data.get("name", ""),
            "google_id": user_data.get("sub"),
            "slug": token_request.slug,
            "created_at": current_time,
            "updated_at": current_time
        }

        result = supabase.table("users").insert(new_user).execute()
        
        if not result.data:
            # Rollback auth user creation if custom table insert fails
            # You might want to add code here to delete the auth user
            raise HTTPException(status_code=400, detail="Failed to create user profile")

        user = result.data[0]
        access_token = create_access_token(data={"sub": user["email"]})

        return {
            "success": True,
            "isComplete": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": user["email"],
                "full_name": user["full_name"],
                "slug": user["slug"]
            }
        }
    except HTTPException as http_error:
        return JSONResponse(
            status_code=http_error.status_code,
            content={
                "success": False,
                "error": {
                    "code": http_error.detail.get("code", "UNKNOWN_ERROR"),
                    "message": http_error.detail.get("message", str(http_error.detail))
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
        current_time = datetime.utcnow().isoformat()  # Convert datetime to string
        new_user = {
            "email": user.email,
            "full_name": user.full_name,
            "hashed_password": hashed_password,
            "slug": user.slug,  # Add the slug field here
            "created_at": current_time,  # ISO 8601 string
            "updated_at": current_time  # ISO 8601 string
        }

        # Insert the user into Supabase table
        result = supabase.table("users").insert(new_user).execute()

        if result.data and isinstance(result.data, list):
            return result.data[0]
        else:
            raise HTTPException(status_code=400, detail="Error inserting user into custom users table")

    except Exception as e:
        print(f"Error: {e}")
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



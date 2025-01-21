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


class GoogleTokenRequest(BaseModel):
    id_token: str
    slug: str = None  # Add slug field for Google signup

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

        if not user_data.get("email"):
            raise HTTPException(status_code=400, detail="Email not found in token")

        # Check if user exists in Supabase users table by email or google_id
        result = supabase.table("users").select("*").or_(
            f"email.eq.{user_data['email']},google_id.eq.{user_data.get('sub')}"
        ).execute()

        if result.data:
            user = result.data[0]  # Existing user found
            
            # Update google_id if not set
            if not user.get("google_id"):
                supabase.table("users").update({
                    "google_id": user_data.get("sub"),
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", user["id"]).execute()
        else:
            # User does not exist, create new user with a random password
            random_password = generate_random_password()

            # Sign up the user with the random password
            auth_user = supabase.auth.sign_up({
                "email": user_data["email"],
                "password": random_password,
            })

            if not hasattr(auth_user, 'user'):
                raise HTTPException(status_code=400, detail="Error creating user in Supabase Auth")

            current_time = datetime.utcnow().isoformat()
            new_user = {
                "email": user_data["email"],
                "full_name": user_data.get("name", ""),
                "hashed_password": "",  # No password for OAuth users
                "google_id": user_data.get("sub"),  # Store Google's user ID
                "created_at": current_time,
                "updated_at": current_time
            }

            if token_request.slug:
                # Check if slug is available
                slug_check = supabase.table("users").select("id").eq("slug", token_request.slug).execute()
                if not slug_check.data:
                    new_user["slug"] = token_request.slug

            result = supabase.table("users").insert(new_user).execute()
            if not result.data:
                raise HTTPException(status_code=400, detail="Failed to create user in custom users table")

            user = result.data[0]

        # Create an access token for the user
        access_token = create_access_token(data={"sub": user["email"]})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": user["email"],
                "full_name": user["full_name"],
                "slug": user.get("slug")
            }
        }

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


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



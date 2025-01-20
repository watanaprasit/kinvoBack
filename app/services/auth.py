# services/auth.py
import httpx
from fastapi import HTTPException
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_supabase
from datetime import datetime

async def validate_google_oauth_token(id_token: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={id_token}")
            if response.status_code != 200:
                raise ValueError(response.json().get('error_description', 'Token validation failed'))
            return response.json()
    except Exception as e:
        raise ValueError(f"Token validation failed: {str(e)}")

class AuthService:
    @staticmethod
    async def register_user(email: str, password: str, full_name: str = None, slug: str = None):
        supabase = get_supabase()
        
        # Check if email exists
        existing = supabase.table("users").select("*").eq("email", email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if slug is taken
        if slug:
            slug_check = supabase.table("users").select("*").eq("slug", slug).execute()
            if slug_check.data:
                raise HTTPException(status_code=400, detail="Slug already taken")

        # Create auth user
        auth_user = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        if not auth_user.user:
            raise HTTPException(status_code=400, detail="Failed to create auth user")

        # Create user in custom table
        current_time = datetime.utcnow().isoformat()
        new_user = {
            "email": email,
            "full_name": full_name,
            "slug": slug,
            "hashed_password": get_password_hash(password),
            "created_at": current_time,
            "updated_at": current_time
        }

        result = supabase.table("users").insert(new_user).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def login_user(email: str, password: str):
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("email", email).execute()
        
        if not result.data:
            raise HTTPException(status_code=401, detail="Incorrect email or password")
            
        user = result.data[0]
        if not verify_password(password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
            
        access_token = create_access_token(data={"sub": user["email"]})
        return {"access_token": access_token, "token_type": "bearer"}

    @staticmethod
    async def google_auth(token_data: dict):
        supabase = get_supabase()
        email = token_data.get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in token")

        # Check if user exists
        result = supabase.table("users").select("*").eq("email", email).execute()
        user = result.data[0] if result.data else None

        if not user:
            # Create new user
            current_time = datetime.utcnow().isoformat()
            new_user = {
                "email": email,
                "full_name": token_data.get("name"),
                "google_id": token_data.get("sub"),
                "created_at": current_time,
                "updated_at": current_time
            }
            
            result = supabase.table("users").insert(new_user).execute()
            user = result.data[0] if result.data else None

            if not user:
                raise HTTPException(status_code=400, detail="Failed to create user")

        # Create access token
        access_token = create_access_token(data={"sub": email})
        return {"access_token": access_token, "token_type": "bearer"}
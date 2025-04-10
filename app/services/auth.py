# services/auth.py
import httpx
from fastapi import HTTPException
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_supabase
from datetime import datetime
import random
import string

def generate_random_password(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=length))

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
    async def handle_google_auth(token_data: dict, is_login: bool = False, slug: str = None):
        supabase = get_supabase()
        email = token_data.get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in token")

        # Check if user exists
        result = supabase.table("users").select("*").eq("email", email).execute()
        existing_user = result.data[0] if result.data else None

        if is_login:
            if not existing_user:
                raise HTTPException(status_code=401, detail="No account found with this email")
            
            # Create access token and return user data
            access_token = create_access_token(data={"sub": email})
            return {
                "success": True,
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "email": existing_user["email"],
                    "full_name": existing_user["full_name"],
                    "slug": existing_user["slug"]
                }
            }
        else:
            # Handle signup
            if existing_user:
                raise HTTPException(
                    status_code=422,
                    detail={"message": "User already exists", "code": "USER_EXISTS"}
                )

            if not slug:
                # First step of registration - just return user info
                return {
                    "email": email,
                    "name": token_data.get("name", ""),
                    "success": True
                }

            # Create user in Supabase Auth
            random_password = generate_random_password()
            auth_user = supabase.auth.sign_up({
                "email": email,
                "password": random_password,
                "options": {
                    "data": {
                        "full_name": token_data.get("name", ""),
                        "google_id": token_data.get("sub")
                    }
                }
            })

            if not auth_user.user:
                raise HTTPException(status_code=400, detail="Error creating user in Supabase Auth")

            # Create user in custom table
            current_time = datetime.utcnow().isoformat()
            new_user = {
                "email": email,
                "full_name": token_data.get("name", ""),
                "google_id": token_data.get("sub"),
                "slug": slug,
                "created_at": current_time,
                "updated_at": current_time
            }

            result = supabase.table("users").insert(new_user).execute()
            
            if not result.data:
                raise HTTPException(status_code=400, detail="Failed to create user profile")

            user = result.data[0]
            access_token = create_access_token(data={"sub": email})

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

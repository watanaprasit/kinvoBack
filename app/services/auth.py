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
                raise HTTPException(status_code=400, detail="Failed to create user record")

            user = result.data[0]
            
            # Create the user profile in user_profiles table
            from app.schemas.user.profile import UserProfileCreate
            from app.services.user_profile import UserProfileService
            
            try:
                # Create basic profile with minimal info
                profile_data = UserProfileCreate(
                    user_id=user["id"],  # Include the user_id here
                    display_name=token_data.get("name", ""),
                    slug=slug,
                    title="",
                    bio="",
                    email=email,
                    website=None,
                    contact=None
                )
                
                # Create the profile
                profile_result = await UserProfileService.create_profile(
                    user_id=user["id"],  # This is redundant but maintains compatibility
                    profile_data=profile_data
                )
            except Exception as e:
                # Log the error and propagate it with a meaningful message
                import traceback
                traceback_str = traceback.format_exc()
                print(f"Error creating user profile: {str(e)}\n{traceback_str}")
                
                # Delete the user to maintain consistency
                try:
                    supabase.table("users").delete().eq("id", user["id"]).execute()
                except Exception as delete_error:
                    print(f"Failed to clean up user after profile creation error: {str(delete_error)}")
                    
                raise HTTPException(
                    status_code=500, 
                    detail=f"Registration failed: Error creating user profile: {str(e)}"
                )
            
            # Generate access token
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
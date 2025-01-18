from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from supabase import create_client, Client
from ...schemas.user import UserCreate, UserLogin, Token, UserResponse
from ...core.config import settings
from ...core.security import create_access_token, get_password_hash, verify_password

router = APIRouter()
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    try:
        # Check if user exists
        existing_user = supabase.table("users").select("*").eq("email", user.email).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = get_password_hash(user.password)
        new_user = {
            "email": user.email,
            "full_name": user.full_name,
            "hashed_password": hashed_password
        }
        
        result = supabase.table("users").insert(new_user).execute()
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    try:
        # Get user from database
        result = supabase.table("users").select("*").eq("email", user_credentials.email).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
            
        user = result.data[0]
        if not verify_password(user_credentials.password, user["hashed_password"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
            
        # Create access token
        access_token = create_access_token(
            data={"sub": user["email"]}
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
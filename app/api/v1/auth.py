from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
from ...schemas.user import UserCreate, UserLogin, Token, UserResponse
from ...core.config import settings
from ...core.security import create_access_token, get_password_hash, verify_password

router = APIRouter()
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    try:
    
        # Fetch users from Supabase Auth
        users_response = supabase.auth.admin.list_users()

        # Check if the response is a list (as the response is not a dictionary with a 'users' key)
        if not isinstance(users_response, list):
            raise HTTPException(status_code=500, detail="Unable to fetch users from Supabase Auth")

        # Check if the email already exists in the Supabase Auth users list
        existing_user = next((u for u in users_response if u.user_metadata.get('email') == user.email), None)

        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Register the user in Supabase Auth using correct method
        auth_user = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })

        # Check if user was successfully created in Supabase Auth
        if not auth_user.user:
            raise HTTPException(status_code=400, detail="Error creating user in Supabase Auth")

        # Create new user record in your custom users table
        hashed_password = get_password_hash(user.password)
        new_user = {
            "email": user.email,
            "full_name": user.full_name,
            "hashed_password": hashed_password
        }

        # Insert user data into your custom users table
        result = supabase.table("users").insert(new_user).execute()

        # Return the user information from the custom table
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

        access_token = create_access_token(
            data={"sub": user["email"]}
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

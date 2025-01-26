# core/security.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from app.db.session import get_supabase
from app.core.config import settings
from app.schemas.user.user import UserResponse

# OAuth2 password bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")  # Using email as the subject

        if email is None:
            raise credentials_exception

        supabase = get_supabase()
        user_data = supabase.table("users").select("*").eq("email", email).execute()

        if not user_data.data:
            raise credentials_exception

        user = user_data.data[0]
        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            slug=user["slug"],
            created_at=user["created_at"],
            updated_at=user["updated_at"],
            google_id=user.get("google_id")
        )

    except JWTError:
        raise credentials_exception
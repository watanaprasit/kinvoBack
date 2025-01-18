from app.services.auth import hash_password, verify_password
from app.core.security import create_access_token

def test_password_hashing():
    password = "securepassword"
    hashed_password = hash_password(password)
    assert verify_password(password, hashed_password)

def test_invalid_password():
    password = "securepassword"
    hashed_password = hash_password(password)
    assert not verify_password("wrongpassword", hashed_password)

def test_create_access_token():
    token = create_access_token({"sub": "test@example.com"})
    assert isinstance(token, str)
    assert len(token.split(".")) == 3  # Valid JWT format

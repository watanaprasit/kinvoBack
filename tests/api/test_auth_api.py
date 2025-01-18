import pytest
from fastapi.testclient import TestClient
from app.main import app  

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_register_user(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword",
        "full_name": "Test User"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_register_existing_user(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword",
        "full_name": "Test User"
    })
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword",
        "full_name": "Test User"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_user(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword",
        "full_name": "Test User"
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "securepassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

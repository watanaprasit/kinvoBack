import pytest

@pytest.fixture
def setup_test_user(client):
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword",
        "full_name": "Test User"
    })

def test_register_and_login_flow(client):
    # Register a user
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword",
        "full_name": "Test User"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

    # Login with the same user
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "securepassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

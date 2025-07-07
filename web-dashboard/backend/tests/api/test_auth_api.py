import pytest
from fastapi.testclient import TestClient
from jose import jwt # For decoding token in test assertions

# Reverted to relative imports for running pytest from web-dashboard/backend
from main import app
from services.auth_service import MOCK_USERS_DB, get_password_hash, SECRET_KEY, ALGORITHM, create_access_token
from models.auth_models import UserCreate # For /register payload

API_V1_PREFIX = "/api/v1" # As defined in main.py

@pytest.fixture(scope="module")
def client():
    # Setup: Ensure known users exist for login tests
    # MOCK_USERS_DB is globally defined in auth_service.py and might be modified by tests.
    # For more robust tests, consider resetting or scoping the mock DB.
    if "testloginuser" not in MOCK_USERS_DB: # Ensure user for positive login test
        MOCK_USERS_DB["testloginuser"] = {
            "username": "testloginuser", "email": "testlogin@example.com", "full_name": "Test Login User",
            "hashed_password": get_password_hash("testloginpass"), "disabled": False,
        }
    if "disabledtestuser" not in MOCK_USERS_DB: # Ensure disabled user
         MOCK_USERS_DB["disabledtestuser"] = {
            "username": "disabledtestuser", "email": "disabledlogin@example.com", "full_name": "Disabled Login User",
            "hashed_password": get_password_hash("disabledpass"), "disabled": True,
        }
    # Clean up user potentially created by registration test, before client yield
    MOCK_USERS_DB.pop("newtestuser", None)

    with TestClient(app) as c:
        yield c

    # Teardown: Clean up users created specifically for this module's tests if necessary.
    # MOCK_USERS_DB.pop("testloginuser", None)
    # MOCK_USERS_DB.pop("disabledtestuser", None)
    # MOCK_USERS_DB.pop("newtestuser", None) # Cleaned before yield as well

# --- Test /api/v1/auth/token ---
def test_login_for_access_token_success(client: TestClient):
    response = client.post(
        f"{API_V1_PREFIX}/auth/token",
        data={"username": "testloginuser", "password": "testloginpass"} # Form data
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Optionally decode token to verify 'sub'
    payload = jwt.decode(token_data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testloginuser"

def test_login_for_access_token_incorrect_password(client: TestClient):
    response = client.post(
        f"{API_V1_PREFIX}/auth/token",
        data={"username": "testloginuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401 # Unauthorized
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_for_access_token_user_not_found(client: TestClient):
    response = client.post(
        f"{API_V1_PREFIX}/auth/token",
        data={"username": "nonexistentuser", "password": "somepassword"}
    )
    assert response.status_code == 401 # Unauthorized
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_for_access_token_disabled_user(client: TestClient):
    response = client.post(
        f"{API_V1_PREFIX}/auth/token",
        data={"username": "disabledtestuser", "password": "disabledpass"}
    )
    assert response.status_code == 400 # Bad Request (as per auth_api.py logic)
    assert response.json()["detail"] == "Inactive user"

# --- Test /api/v1/auth/register ---
def test_register_user_success(client: TestClient):
    new_user_data = {
        "username": "newtestuser",
        "email": "new@example.com",
        "full_name": "New Test User",
        "password": "newpassword123"
    }
    response = client.post(f"{API_V1_PREFIX}/auth/register", json=new_user_data)
    assert response.status_code == 201 # Created
    user_response = response.json()
    assert user_response["username"] == new_user_data["username"]
    assert user_response["email"] == new_user_data["email"]
    assert user_response["full_name"] == new_user_data["full_name"]
    assert user_response["disabled"] is False

    # Verify user was added to mock DB (and password was hashed)
    assert "newtestuser" in MOCK_USERS_DB
    assert MOCK_USERS_DB["newtestuser"]["hashed_password"] != new_user_data["password"]

def test_register_user_username_already_exists(client: TestClient):
    # Use an existing user from the mock DB setup or one created by a previous test
    existing_user_data = {
        "username": "testloginuser", # This user is created in the client fixture
        "email": "another@example.com",
        "full_name": "Another User",
        "password": "anotherpassword"
    }
    response = client.post(f"{API_V1_PREFIX}/auth/register", json=existing_user_data)
    assert response.status_code == 400 # Bad Request
    assert response.json()["detail"] == "Username already registered"

def test_register_user_invalid_payload(client: TestClient):
    # Missing password
    invalid_payload = {
        "username": "invaliduser",
        "email": "invalid@example.com"
    }
    response = client.post(f"{API_V1_PREFIX}/auth/register", json=invalid_payload)
    assert response.status_code == 422 # Unprocessable Entity (FastAPI validation)
    # Check for detail about missing password field
    assert any("password" in error["loc"] and error["type"] == "missing" for error in response.json()["detail"])

# --- Test /api/v1/health (Public endpoint) ---
def test_health_check(client: TestClient):
    response = client.get(f"{API_V1_PREFIX}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Web Dashboard Backend is healthy"}

# --- Test /api/v1/protected-data (Protected endpoint) ---
def test_get_protected_data_unauthenticated(client: TestClient):
    response = client.get(f"{API_V1_PREFIX}/protected-data")
    # The AuthMiddleware should return 401 if no token is provided
    assert response.status_code == 401
    # The content might vary based on how AuthMiddleware constructs the response for "Not authenticated"
    # For this example, we expect "Not authenticated" or a JSON detail
    content = response.json() if response.headers.get('content-type') == 'application/json' else response.text
    if isinstance(content, dict):
        assert "Not authenticated" in content.get("detail", "") or "Not authenticated" in content
    else: # if it's plain text
        assert "Not authenticated" in content

def test_get_protected_data_authenticated(client: TestClient):
    # 1. Login to get a token
    login_response = client.post(
        f"{API_V1_PREFIX}/auth/token",
        data={"username": "testloginuser", "password": "testloginpass"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # 2. Use the token to access the protected route
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"{API_V1_PREFIX}/protected-data", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "This is protected data." in data["message"]
    assert data["user"]["username"] == "testloginuser"

def test_get_protected_data_with_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer aninvalidtoken"}
    response = client.get(f"{API_V1_PREFIX}/protected-data", headers=headers)
    assert response.status_code == 401 # Unauthorized
    assert "Invalid or expired token" in response.json()["detail"]

def test_get_protected_data_with_disabled_user_token(client: TestClient):
    # 1. Login as disabled user (this should fail at login, but if a token was somehow obtained)
    # For this test, let's assume a token for a disabled user was created directly for testing this scenario.
    # We'll use the 'disabledtestuser' which auth_service.MOCK_USERS_DB marks as disabled.

    # Manually create a token for the disabled user for this test case,
    # as login endpoint would prevent it.
    from services.auth_service import create_access_token # Import here for clarity
    disabled_user_token = create_access_token(data={"sub": "disabledtestuser"})

    headers = {"Authorization": f"Bearer {disabled_user_token}"}
    response = client.get(f"{API_V1_PREFIX}/protected-data", headers=headers)
    # AuthMiddleware should catch this
    assert response.status_code == 403 # Forbidden (or 401, depending on middleware's choice for disabled)
    assert "User account is disabled" in response.json()["detail"]

# Note: To run these, ensure `web-dashboard/backend` is the CWD or project root with PYTHONPATH.
# Example from project root: PYTHONPATH=. pytest web-dashboard/backend/tests/api/test_auth_api.py
# Needs `python-multipart` for form data: pip install python-multipart (should be in main Dockerfile's reqs)

import pytest
from jose import jwt
from freezegun import freeze_time
import datetime

# Reverted to relative imports for running pytest from web-dashboard/backend
from services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    MOCK_USERS_DB, # For checking test user details
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

@pytest.fixture
def test_user_password():
    return "testpassword"

@pytest.fixture
def test_user_hashed_password(test_user_password):
    # This relies on MOCK_USERS_DB using the same hashing for "testuser"
    # Or, hash it freshly if MOCK_USERS_DB isn't pre-populated as expected for tests
    # For simplicity, we'll assume "testuser" in MOCK_USERS_DB has "testpassword"
    user_details = MOCK_USERS_DB.get("testuser")
    if user_details:
        return user_details["hashed_password"]
    return get_password_hash(test_user_password) # Fallback if testuser not in mock

def test_get_password_hash(test_user_password):
    hashed = get_password_hash(test_user_password)
    assert hashed is not None
    assert hashed != test_user_password

def test_verify_password(test_user_password, test_user_hashed_password):
    assert verify_password(test_user_password, test_user_hashed_password) is True
    assert verify_password("wrongpassword", test_user_hashed_password) is False

def test_create_access_token():
    username = "testuser"
    with freeze_time("2024-01-01 12:00:00"):
        token = create_access_token(data={"sub": username})
        assert token is not None

        # Decode to check payload (without full verification, just structure)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == username
        expected_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        # Allow a small delta for timestamp comparison due to float precision
        assert abs(payload["exp"] - expected_exp.timestamp()) < 2

def test_create_access_token_with_custom_expiry():
    username = "testuser_custom_exp"
    custom_delta = datetime.timedelta(hours=1)
    with freeze_time("2024-01-01 12:00:00"):
        token = create_access_token(data={"sub": username}, expires_delta=custom_delta)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == username
        expected_exp = datetime.datetime.now(datetime.timezone.utc) + custom_delta
        assert abs(payload["exp"] - expected_exp.timestamp()) < 2

def test_decode_valid_access_token():
    username = "testuser_decode"
    token = create_access_token(data={"sub": username})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == username

def test_decode_expired_access_token():
    username = "testuser_expired"
    # Create a token that expired in the past
    expired_delta = datetime.timedelta(minutes=-(ACCESS_TOKEN_EXPIRE_MINUTES + 5))

    # Can't use freeze_time to make it *currently* expired in a simple way for create_access_token
    # as it calculates expiry from 'now'.
    # Instead, let's manually craft an expired token payload for testing decode_access_token

    # Create a token that would have been valid if 'now' was in the past
    past_now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 2)

    to_encode = {"sub": username, "exp": past_now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}
    expired_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    payload = decode_access_token(expired_token)
    assert payload is None # decode_access_token should return None for expired tokens due to JWTError

def test_decode_invalid_token_signature():
    invalid_token = "this.is.not_a_valid_jwt_token"
    payload = decode_access_token(invalid_token)
    assert payload is None

    # Token with valid structure but wrong secret
    username = "testuser_wrong_secret"
    token_good_struct = create_access_token(data={"sub": username})
    parts = token_good_struct.split('.')
    # Tamper with signature or use a token signed with a different key
    # For simplicity, just test with a structurally invalid one again or a known bad one.
    # A more robust test would be to create a token with a different secret.

    # Create a token with a different secret
    wrong_secret_key = "another_secret_entirely"
    token_wrong_secret = jwt.encode({"sub": username, "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)}, wrong_secret_key, algorithm=ALGORITHM)

    payload_wrong_secret = decode_access_token(token_wrong_secret)
    assert payload_wrong_secret is None

def test_decode_token_missing_sub():
    # Token missing 'sub' claim
    exp_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_no_sub = jwt.encode({"exp": exp_time}, SECRET_KEY, algorithm=ALGORITHM)
    payload = decode_access_token(token_no_sub)
    # decode_access_token itself doesn't validate 'sub', it just decodes.
    # The consumer of decode_access_token (like get_current_user) would check for 'sub'.
    # So, this should successfully decode if structure and signature are fine.
    assert payload is not None
    assert "sub" not in payload

# To run these tests, navigate to `web-dashboard/backend` and run `pytest`
# Ensure `freezegun` is installed: pip install freezegun
# PYTHONPATH needs to be set up so that `from services.auth_service` works.
# If running pytest from `web-dashboard/backend`, it should work if tests/ is a subdir.
# If running from project root: `PYTHONPATH=. pytest web-dashboard/backend/tests`
# Need to install freezegun: pip install freezegun
# (I will run `pip install freezegun` in the next step)

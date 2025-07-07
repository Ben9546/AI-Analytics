import datetime # Keep this for timedelta
from datetime import timezone, timedelta # Specific imports
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# Conceptual: Import settings from a central config
# from ..config.settings import AppSettings
# settings = AppSettings()

SECRET_KEY = "your_very_secret_jwt_key_for_dashboard"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MOCK_USERS_DB = {
    "testuser": {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": pwd_context.hash("testpassword"),
        "disabled": False,
    },
    "disableduser": {
        "username": "disableduser",
        "email": "disabled@example.com",
        "full_name": "Disabled User",
        "hashed_password": pwd_context.hash("disabledpassword"),
        "disabled": True,
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_user_from_db(username: str) -> Optional[dict]:
    if username in MOCK_USERS_DB:
        return MOCK_USERS_DB[username]
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes a JWT access token.
    Returns the payload if the token is valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# --- OAuth2 Password Bearer Flow (Conceptual Dependencies) ---
# FastAPI uses these for dependency injection in route operations.
# from fastapi.security import OAuth2PasswordBearer
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token") # Matches the token endpoint

# async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[UserInDB]:
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     payload = decode_access_token(token)
#     if payload is None:
#         raise credentials_exception
#     username: str = payload.get("sub")
#     if username is None:
#         raise credentials_exception
#     user_dict = get_user_from_db(username)
#     if user_dict is None:
#         raise credentials_exception
#     user = UserInDB(**user_dict) # Assuming UserInDB model exists
#     return user

# async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
#     if current_user.disabled:
#         raise HTTPException(status_code=400, detail="Inactive user")
#     return current_user

# Note: The Depends and HTTPException parts are commented out as they are typically used
# directly in endpoint definitions or middleware, not as standalone service functions.
# The core logic (create_access_token, decode_access_token, user lookup) is what's important here.
# The UserInDB model would come from models.auth_models
# from ..models.auth_models import UserInDB
# from fastapi import Depends, HTTPException, status (these would be needed for the commented section)

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Standard form for username/password
from datetime import timedelta

# Adjusted to be absolute from 'backend' perspective
from services.auth_service import (
    MOCK_USERS_DB,
    verify_password,
    create_access_token,
    get_user_from_db,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from models.auth_models import Token, UserCreate, UserBase # Assuming UserBase can be used for response

router = APIRouter()

@router.post("/token", response_model=Token, summary="Login and get access token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token endpoint.
    Takes username and password from form data.
    """
    user_dict = get_user_from_db(form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_is_disabled = user_dict.get("disabled", False)
    if user_is_disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Or 403 Forbidden
            detail="Inactive user",
        )

    if not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserBase, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register_user(user: UserCreate):
    """
    Registers a new user.
    (Conceptual: In a real app, save to database)
    """
    if user.username in MOCK_USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    hashed_password = get_password_hash(user.password)
    # Create new user in our mock DB
    MOCK_USERS_DB[user.username] = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hashed_password,
        "disabled": False # New users are active by default
    }
    print(f"Mock User Registered: {user.username}")
    # Return basic user info (without password)
    return UserBase(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=False
    )

# Example protected endpoint (to be moved to a different router later)
# from ..models.auth_models import UserInDB (if you have this Pydantic model)
# from ..services.auth_service import get_current_active_user (if using FastAPI's Depends system for auth)

# @router.get("/users/me", summary="Get current authenticated user's details")
# async def read_users_me(current_user_data: dict = Depends(get_current_active_user_from_middleware_state_conceptual)):
#     # This dependency would need to be created to extract user from request.state.current_user
#     # For now, this endpoint is more conceptual as middleware handles auth for other routes.
#     # If using middleware, the user info is in request.state.current_user on protected routes.
#     # This endpoint itself wouldn't need the middleware to re-check if it's set up globally.
#     # A dependency function could be:
#     # async def get_current_active_user_from_request_state(request: Request):
#     #    if not hasattr(request.state, "current_user") or not request.state.current_user:
#     #        raise HTTPException(status_code=401, detail="Not authenticated by middleware")
#     #    user = request.state.current_user
#     #    if user.get("disabled"):
#     #        raise HTTPException(status_code=400, detail="Inactive user")
#     #    return user
#     # current_user_data: dict = Depends(get_current_active_user_from_request_state)
#     return {"message": "This endpoint would show current user if middleware is fully integrated with a dependency."}

# To test the middleware, other non-auth endpoints will be created later.
# The middleware will protect those.
# The /token and /register endpoints are typically public.
# The AuthMiddleware has PUBLIC_PATHS to exclude these.

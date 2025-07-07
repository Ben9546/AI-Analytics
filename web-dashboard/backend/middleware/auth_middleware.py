from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse # Import JSONResponse
from typing import Optional, Callable, Awaitable

from services.auth_service import decode_access_token, get_user_from_db

PUBLIC_PATHS = [
    "/api/v1/health",
    "/api/v1/auth/token",
    "/api/v1/auth/register",
    "/docs",
    "/openapi.json",
    "/ws/realtime/"
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if any(request.url.path.startswith(public_path) for public_path in PUBLIC_PATHS):
            response = await call_next(request)
            return response

        authorization: Optional[str] = request.headers.get("Authorization")
        scheme, _, param = "", "", ""
        if authorization:
            parts = authorization.split()
            if len(parts) == 2:
                scheme, param = parts[0], parts[1]
            elif len(parts) == 1:
                scheme = "bearer"
                param = parts[0]

        if not authorization or scheme.lower() != "bearer" or not param:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = param
        payload = decode_access_token(token)

        if payload is None:
            return JSONResponse( # Return JSONResponse instead of raising HTTPException
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        username: Optional[str] = payload.get("sub")
        if username is None:
            return JSONResponse( # Return JSONResponse
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token payload invalid: missing username"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = get_user_from_db(username)
        if user is None:
            return JSONResponse( # Return JSONResponse
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "User not found for token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.get("disabled"):
             return JSONResponse( # Return JSONResponse
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "User account is disabled"},
            )

        request.state.current_user = user

        try:
            response = await call_next(request)
            return response
        except HTTPException as http_exc:
            raise http_exc # Re-raise app-level HTTPExceptions
        except Exception as e:
            print(f"Unhandled exception after auth: {e}")
            # For unexpected errors, it's still okay to raise HTTPException
            # or return a JSONResponse
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error after authentication."}
            )

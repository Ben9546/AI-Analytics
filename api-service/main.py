from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from contextlib import asynccontextmanager
import time
from typing import Dict, List, Any

# --- Mock API Key Store ---
MOCK_API_KEYS = {
    "testapikey123": {"client_id": "client_a", "permissions": ["read", "write"]},
    "readonlykey456": {"client_id": "client_b", "permissions": ["read"]},
}

api_key_header_auth = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header_auth)):
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated: X-API-KEY header missing.")
    key_details = MOCK_API_KEYS.get(api_key)
    if not key_details:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key.")
    return key_details

# --- Rate Limiting (Simple In-Memory) ---
RATE_LIMIT_MAX_REQUESTS_API = 50
RATE_LIMIT_WINDOW_SECONDS_API = 60
request_counts_api: Dict[str, List[float]] = {}

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    print("--- API Service Starting Up (Lifespan) ---")
    yield
    print("--- API Service Shutting Down (Lifespan) ---")

app = FastAPI(
    title="Business AI API Service",
    description="API access for enterprise integrations.",
    version="v1",
    lifespan=lifespan
)

@app.middleware("http")
async def rate_limit_api_middleware(request: Request, call_next):
    # Identify client by API key if available, otherwise IP
    api_key_in_header = request.headers.get("X-API-KEY")
    identifier = api_key_in_header if api_key_in_header else request.client.host if request.client else "unknown_ip"

    current_time = time.time()
    if identifier not in request_counts_api:
        request_counts_api[identifier] = []

    request_timestamps = request_counts_api[identifier]
    request_timestamps = [ts for ts in request_timestamps if ts > current_time - RATE_LIMIT_WINDOW_SECONDS_API]

    if len(request_timestamps) >= RATE_LIMIT_MAX_REQUESTS_API:
        time_to_wait = (request_timestamps[0] + RATE_LIMIT_WINDOW_SECONDS_API) - current_time
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {identifier}. Try again in {max(0, round(time_to_wait))} seconds.",
            headers={"Retry-After": str(int(max(0, time_to_wait)))}
        ) # Note: Middleware should return Response, but TestClient handles HTTPException directly.
          # For robust middleware, return JSONResponse. This is simplified for now.

    request_timestamps.append(current_time)
    request_counts_api[identifier] = request_timestamps

    response = await call_next(request)
    return response

# --- Routers ---
# Assuming main.py is in 'api-service' and 'endpoints' is a direct subdirectory.
# These imports should work if running python -m pytest from 'api-service' CWD.
from endpoints.data_ingestion import router as ingestion_router
from endpoints.analytics import router as analytics_router
# Import other routers as they are created:
# from endpoints.forecasting import router as forecasting_router
# from endpoints.recommendations import router as recommendations_router
# from endpoints.webhooks import router as webhooks_router

API_PREFIX_V1 = "/api/v1" # Central definition for prefix

app.include_router(ingestion_router, prefix=f"{API_PREFIX_V1}/data", tags=["Data Ingestion"], dependencies=[Depends(verify_api_key)])
app.include_router(analytics_router, prefix=f"{API_PREFIX_V1}/analytics", tags=["Analytics"], dependencies=[Depends(verify_api_key)])
# app.include_router(forecasting_router, prefix=f"{API_PREFIX_V1}/forecasting", tags=["Forecasting"], dependencies=[Depends(verify_api_key)])
# app.include_router(recommendations_router, prefix=f"{API_PREFIX_V1}/recommendations", tags=["Recommendations"], dependencies=[Depends(verify_api_key)])
# app.include_router(webhooks_router, prefix=f"{API_PREFIX_V1}/webhooks", tags=["Webhooks"], dependencies=[Depends(verify_api_key)])


@app.get(f"{API_PREFIX_V1}/health", tags=["System"])
async def health_check():
    return {"status": "ok", "message": "API Service is healthy"}

@app.get(f"{API_PREFIX_V1}/me", tags=["Authentication"], dependencies=[Depends(verify_api_key)])
async def read_current_client(key_details: dict = Depends(verify_api_key)):
    return {"client_id": key_details["client_id"], "permissions": key_details["permissions"]}

if __name__ == "__main__":
    import uvicorn
    # PYTHONPATH=. uvicorn api_service.main:app --reload --port 8020 (from business-ai-analytics root)
    print("To run this app, navigate to project root and run: PYTHONPATH=. uvicorn api_service.main:app --reload --port 8020")

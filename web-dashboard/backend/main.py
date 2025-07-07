from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager # For lifespan events

# Adjusted imports to be absolute from 'backend' directory's perspective
from config.settings import AppSettings # Conceptual settings import
from middleware.auth_middleware import AuthMiddleware
from api.auth_api import router as auth_router
from api.dashboard_api import router as dashboard_api_router
from api.integrations_api import router as integrations_api_router

# Conceptual: Load settings
# settings = AppSettings()

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Code to run on startup
    print("--- Web Dashboard Backend Starting Up (Lifespan) ---")
    # print(f"AppSettings loaded: {settings.dict()}") # If settings were real
    # await init_db(settings.database_url) # Initialize DB
    print(f"PostgreSQL connection: Conceptual (not implemented yet)")
    print(f"Redis connection: Conceptual (not implemented yet)")
    # Example: asyncio.create_task(periodic_broadcast()) # If you had such a task
    yield
    # Code to run on shutdown
    # await close_db_connections() # Close DB
    print("--- Web Dashboard Backend Shutting Down (Lifespan) ---")

app = FastAPI(
    title="Web Dashboard Backend API",
    description="Backend services for the Business AI Analytics Web Dashboard.",
    version="0.1.0",
    lifespan=lifespan # Use the new lifespan context manager
    # root_path=settings.api_v1_prefix
)

# --- Middleware ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    # settings.frontend_url
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)


# --- API Routers ---
API_V1_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=f"{API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(dashboard_api_router, prefix=f"{API_V1_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(integrations_api_router, prefix=f"{API_V1_PREFIX}/integrations", tags=["Integrations"])


@app.get(f"{API_V1_PREFIX}/health", tags=["System"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "message": "Web Dashboard Backend is healthy"}

@app.get(f"{API_V1_PREFIX}/protected-data", tags=["Protected"])
async def get_protected_data(request: Request):
    if not hasattr(request.state, "current_user") or not request.state.current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    current_user_data = request.state.current_user
    return {"message": "This is protected data.", "user": current_user_data}


# --- WebSocket for Real-time Updates (Conceptual) ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New WebSocket connection: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket disconnected: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        print(f"Broadcasting message: {message}")
        active_connections_copy = list(self.active_connections)
        for connection in active_connections_copy:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to {connection.client}: {e}")
                self.disconnect(connection)


manager = ConnectionManager()

@app.websocket("/ws/realtime/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    await manager.send_personal_message(f"Welcome, Client #{client_id}! You are connected for real-time updates.", websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Client #{client_id} says: {data}")
            await manager.send_personal_message(f"Server received your message: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client #{client_id} disconnected from WebSocket (WebSocketDisconnect).")
    except Exception as e:
        print(f"Error in WebSocket for Client #{client_id}: {type(e).__name__} - {e}")
        manager.disconnect(websocket)
        print(f"Client #{client_id} forcefully disconnected due to error.")

async def simulate_realtime_update(message: str):
    print(f"Simulating realtime update: {message}")
    await manager.broadcast(message)

# Example of starting a background task with lifespan
# import asyncio
# from datetime import datetime # Ensure datetime is imported if using it here
# async def periodic_broadcast_task():
#    count = 0
#    while True:
#        await asyncio.sleep(15) # Wait for 15 seconds
#        count += 1
#        await simulate_realtime_update(f"Periodic Server Update #{count} at {datetime.now(timezone.utc).isoformat()}")

# @asynccontextmanager
# async def lifespan_with_task(app_instance: FastAPI):
#     print("--- Web Dashboard Backend Starting Up (Lifespan with Task) ---")
#     task = asyncio.create_task(periodic_broadcast_task())
#     yield
#     print("--- Web Dashboard Backend Shutting Down (Lifespan with Task) ---")
#     task.cancel()
#     try:
#         await task
#     except asyncio.CancelledError:
#         print("Periodic broadcast task cancelled.")
# app = FastAPI(lifespan=lifespan_with_task) # If you want the task


if __name__ == "__main__":
    import uvicorn
    print("To run this app, navigate to the 'business-ai-analytics' project root directory and execute:")
    print("PYTHONPATH=. uvicorn web_dashboard.backend.main:app --reload --port 8010")

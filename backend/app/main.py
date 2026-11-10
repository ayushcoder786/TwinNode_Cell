from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.db.session import engine, Base
from backend.app.api.endpoints import router as api_router
from backend.app.services.supervisor import supervisor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables and launch supervisor background loop
    print("[TwinNode Backend] Initializing database models...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    supervisor.start_background_loop()
    print("[TwinNode Backend] System ready.")
    yield
    # Shutdown
    print("[TwinNode Backend] Shutting down...")
    supervisor._is_running = False
    supervisor.serial_service.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Distributed Sensing and Actuation Supervisor Backend & REST/WebSocket Gateway",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Top-level WebSocket Endpoint for Dashboard
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await supervisor.register_websocket(websocket)
    try:
        while True:
            # Keep connection alive & listen for client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        supervisor.unregister_websocket(websocket)
    except Exception as e:
        supervisor.unregister_websocket(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)

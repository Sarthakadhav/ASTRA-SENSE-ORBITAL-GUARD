import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api.router import api_router
from app.database.init_db import init_database
from app.core.logging import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite flight tables & seed initial mission datasets
    logger.info("Initializing ORBITAL GUARD Onboard Flight Storage...")
    init_database()
    logger.info("Onboard flight systems nominal. Ready for ESP32 streams & flight deck UI.")
    
    # Autonomous background synchronization worker
    sync_task = None
    if settings.SUPABASE_SYNC_ENABLED and (settings.SUPABASE_SECRET_KEY or settings.SUPABASE_SERVICE_ROLE_KEY):
        from app.services.sync_service import sync_service
        async def background_sync_worker():
            logger.info(f"Background Supabase sync worker active (interval: {settings.SUPABASE_SYNC_INTERVAL_SECONDS}s).")
            while True:
                try:
                    await sync_service.process_sync_batch()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Background sync worker iteration error: {e}")
                try:
                    await asyncio.sleep(settings.SUPABASE_SYNC_INTERVAL_SECONDS)
                except asyncio.CancelledError:
                    break

        sync_task = asyncio.create_task(background_sync_worker())

    yield

    # Shutdown
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
    logger.info("ORBITAL GUARD shutting down gracefully.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Cross-Origin Resource Sharing (CORS) for React dashboard, Vite dev server, and ESP32 nodes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount frontend assets if directory exists
assets_dir = settings.STATIC_DIR / "assets"
if assets_dir.exists() and assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/health", tags=["System Health"])
def health_check():
    """Railway health check probe endpoint."""
    return {
        "status": "HEALTHY",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/", tags=["Flight Status"])
async def root(request: Request):
    """
    Root endpoint:
    - Serves React SPA index.html for browser navigation requests.
    - Serves JSON flight status for API clients and automated tests.
    """
    accept = request.headers.get("accept", "")
    index_file = settings.STATIC_DIR / "index.html"

    # Browser navigation requests accept text/html
    if "text/html" in accept and not accept.startswith("*/*"):
        if index_file.is_file():
            return FileResponse(index_file)

    # API callers, test suites, or fallback
    if "application/json" in accept or not index_file.is_file() or accept.startswith("*/*"):
        return {
            "system": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "FLIGHT_ACTIVE",
            "mode": "AUTONOMOUS_EDGE_ENGINE",
            "api_documentation": "/docs",
            "api_v1": settings.API_V1_STR
        }

    if index_file.is_file():
        return FileResponse(index_file)

    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "FLIGHT_ACTIVE",
        "mode": "AUTONOMOUS_EDGE_ENGINE",
        "api_documentation": "/docs",
        "api_v1": settings.API_V1_STR
    }

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_catchall(full_path: str, request: Request):
    """
    SPA catch-all router:
    - Returns JSON 404 for unhandled API routes (/api/v1/*).
    - Returns direct static file matches if they exist.
    - Falls back to index.html for client-side routing.
    """
    # 1. Unhandled API routes MUST return JSON 404, never index.html
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail=f"API endpoint '/{full_path}' not found")

    # 2. Check for matching static files in static directory
    static_file = (settings.STATIC_DIR / full_path).resolve()
    try:
        static_file.relative_to(settings.STATIC_DIR.resolve())
        if static_file.is_file():
            return FileResponse(static_file)
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 3. Fallback to index.html for client-side SPA routing (e.g. /mission-medic, /crew-matrix)
    index_file = settings.STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    # 4. Fallback if frontend is not built
    raise HTTPException(status_code=404, detail=f"Route '/{full_path}' not found")

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled operational fault: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SYSTEM_FAULT",
            "message": "Flight software encountered an unhandled exception. Local autonomous monitoring active.",
            "details": str(exc) if settings.DEBUG else None
        }
    )

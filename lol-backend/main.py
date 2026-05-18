from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.database import init_db, close_db
from app.db.redis import redis_client
from app.services.riot_api_client import RiotAPIError, RateLimitError


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(debug=settings.debug)
    logger = get_logger(__name__)
    logger.info("application_startup", version=settings.app_version)

    await init_db()
    logger.info("database_initialized")

    await redis_client.connect()
    logger.info("redis_initialized")

    yield

    # Shutdown
    logger.info("application_shutdown")
    await redis_client.disconnect()
    await close_db()
    logger.info("resources_cleaned_up")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.exception_handler(RiotAPIError)
async def riot_api_error_handler(_, exc: RiotAPIError):
    """Translate Riot upstream errors to explicit API responses."""
    status_code = 502
    if exc.status_code in (401, 403):
        status_code = 503
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": f"Riot API error ({exc.status_code}): {exc.message}",
            "upstream_status": exc.status_code,
        },
    )


@app.exception_handler(RateLimitError)
async def riot_rate_limit_error_handler(_, exc: RateLimitError):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Riot API rate limited: {exc.message}"},
    )


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

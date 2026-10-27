from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging import get_logger, mask_secret

logger = get_logger("edith_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("EDITH AI Backend starting up...")
    logger.info(f"Target NVIDIA Base URL: {settings.NVIDIA_BASE_URL}")
    logger.info(f"Default Model: {settings.NVIDIA_MODEL}")
    logger.info(f"NVIDIA API Key: {mask_secret(settings.NVIDIA_API_KEY)}")
    logger.info("=" * 60)
    yield
    logger.info("EDITH AI Backend shutting down...")

app = FastAPI(
    title="EDITH AI Assistant Backend",
    description="NVIDIA AI Catalog-powered assistant and structured task planner for the EDITH Android app.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Android clients and web debuggers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

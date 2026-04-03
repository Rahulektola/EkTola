from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from contextlib import asynccontextmanager
import logging

from app.services import admin_routes, auth_routes, contact_routes, campaign_routes, template_routes, analytics_routes, webhook_routes, whatsapp_auth_routes
from app.database import engine, Base
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    logger.info("🎯 Starting EkTola API")
    yield
    logger.info("🛑 Shutting down EkTola API")

# Middleware to add no-cache headers
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add no-cache headers to prevent browser caching issues
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# Initialize FastAPI app
app = FastAPI(
    title="EkTola - WhatsApp Jeweller Platform",
    description="Mobile-first Progressive Web App for jewellers to manage customer contacts and WhatsApp campaigns",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan  # Add lifespan context manager
)

# Add no-cache middleware FIRST (will be innermost)
app.add_middleware(NoCacheMiddleware)

# CORS middleware LAST (will be outermost - handles preflight requests first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(admin_routes.router)
app.include_router(auth_routes.router)
app.include_router(whatsapp_auth_routes.router)
app.include_router(contact_routes.router)
app.include_router(campaign_routes.router)
app.include_router(template_routes.router)
app.include_router(analytics_routes.router)
app.include_router(webhook_routes.router)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "EkTola WhatsApp Jeweller Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False
    )

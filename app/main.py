from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from app.routers import auth, contacts, campaigns, templates, analytics, webhooks
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


# Background task for campaign scheduler
async def run_campaign_scheduler():
    """Background task that runs the campaign scheduler every minute"""
    from app.services.scheduler import campaign_scheduler
    
    logger.info("🚀 Campaign scheduler started")
    
    while True:
        try:
            triggered = campaign_scheduler.check_and_trigger_campaigns()
            if triggered > 0:
                logger.info(f"✅ Triggered {triggered} campaigns")
        except Exception as e:
            logger.error(f"❌ Scheduler error: {str(e)}")
        
        # Wait 60 seconds before next check
        await asyncio.sleep(60)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info("🎯 Starting EkTola API")
    
    # Start campaign scheduler as background task
    scheduler_task = asyncio.create_task(run_campaign_scheduler())
    logger.info("📅 Campaign scheduler initialized")
    
    yield  # Application runs
    
    # Shutdown
    logger.info("🛑 Shutting down EkTola API")
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        logger.info("✅ Scheduler stopped")

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(campaigns.router)
app.include_router(templates.router)
app.include_router(analytics.router)
app.include_router(webhooks.router)


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

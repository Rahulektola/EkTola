from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, contacts, campaigns, templates, analytics, webhooks, admin_panel
from app.database import engine, Base
from app.config import settings

# Create database tables (only if database is available)
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"⚠️ Database connection failed: {e}")
    print("⚠️ App will run but database endpoints won't work")

# Initialize FastAPI app
app = FastAPI(
    title="EkTola - WhatsApp Jeweller Platform",
    description="Mobile-first Progressive Web App for jewellers to manage customer contacts and WhatsApp campaigns",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
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
app.include_router(admin_panel.router)
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

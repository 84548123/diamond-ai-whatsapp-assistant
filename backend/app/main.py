from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from .core.config import settings
from .db.session import init_db
from .db.init_db import initialize_database
from .api.routers import auth, whatsapp, chat, leads, appointments, analytics, stock, dashboard, users
from .services.stock_service import StockService

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting AI WhatsApp Assistant...")
    initialize_database()
    
    # Load stock into memory
    stock_svc = StockService()
    print(f"📦 Stock loaded: {len(stock_svc.df) if stock_svc.df is not None else 0} items")
    
    # TODO: Optional - sync to DB + Chroma
    # stock_svc.sync_to_postgres(...)
    
    yield
    print("👋 Shutting down...")

app = FastAPI(
    title="AI-Powered WhatsApp Assistant",
    description="Production-ready AI assistant for diamond businesses. Supports stock lookup by Rep No / Stone No, WhatsApp auto-reply, CRM, analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(whatsapp.router, prefix="/api/v1/whatsapp", tags=["WhatsApp"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["Stock"])
app.include_router(leads.router, prefix="/api/v1/leads", tags=["Leads"])
app.include_router(appointments.router, prefix="/api/v1/appointments", tags=["Appointments"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(__import__('app.api.routers.stats', fromlist=['router']).router, prefix="/api/v1", tags=["Stats"])

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    return {
        "message": "AI WhatsApp Assistant API",
        "docs": "/docs",
        "health": "/health",
        "stock_query_example": "/api/v1/stock/search?rep_no=1529267932"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if settings.DEBUG else "Contact support"}
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

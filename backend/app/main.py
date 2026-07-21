from contextlib import asynccontextmanager
import os
import uvicorn

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# -----------------------------------------------------
# Configuration
# -----------------------------------------------------

from .core.config import settings

# -----------------------------------------------------
# Database Imports (Optional)
# -----------------------------------------------------

try:
    from .db.init_db import initialize_database
except Exception as e:
    print(f"Database import error: {e}")
    initialize_database = None

# -----------------------------------------------------
# Stock Service (Optional)
# -----------------------------------------------------

try:
    from .services.stock_service import StockService
except Exception as e:
    print(f"Stock service import error: {e}")
    StockService = None

# -----------------------------------------------------
# API Routers (Optional)
# -----------------------------------------------------

try:
    from .api.routers import (
        auth,
        whatsapp,
        chat,
        leads,
        appointments,
        analytics,
        stock,
        dashboard,
        users,
    )
except Exception as e:
    print(f"Router import error: {e}")

try:
    from app.api.routers.stats import router as stats_router
except Exception:
    stats_router = None


# -----------------------------------------------------
# Rate Limiting
# -----------------------------------------------------

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)

except Exception as e:
    print(f"SlowAPI error: {e}")
    limiter = None
    RateLimitExceeded = None
    _rate_limit_exceeded_handler = None


# -----------------------------------------------------
# Lifespan Events
# -----------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("=" * 60)
    print("Starting AI WhatsApp Assistant")
    print("=" * 60)

    # ---------------------------------
    # Database Initialization
    # ---------------------------------

    try:
        if initialize_database:
            initialize_database()
            print("Database initialized successfully.")

    except Exception as e:
        print(f"Database initialization failed: {e}")

    # ---------------------------------
    # Stock Loading
    # ---------------------------------

    try:
        if StockService:

            stock_svc = StockService()

            total_stock = (
                len(stock_svc.df)
                if stock_svc.df is not None
                else 0
            )

            print(f"Stock Loaded : {total_stock}")

    except Exception as e:
        print(f"Stock loading failed: {e}")

    yield

    print("=" * 60)
    print("Shutting down AI WhatsApp Assistant")
    print("=" * 60)


# -----------------------------------------------------
# FastAPI App
# -----------------------------------------------------

app = FastAPI(
    title="AI Powered WhatsApp Assistant",
    description=(
        "Production-ready AI Assistant for Diamond Businesses. "
        "Supports Stock Search, WhatsApp Automation, Analytics "
        "and Lead Management."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# -----------------------------------------------------
# CORS Configuration
# -----------------------------------------------------

try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

except Exception as e:
    print(f"CORS Error : {e}")


# -----------------------------------------------------
# Rate Limiting
# -----------------------------------------------------

try:
    if limiter:

        app.state.limiter = limiter

        app.add_exception_handler(
            RateLimitExceeded,
            _rate_limit_exceeded_handler,
        )

except Exception as e:
    print(f"Rate Limiter Error : {e}")


# -----------------------------------------------------
# Include Routers
# -----------------------------------------------------

def register_router(router, prefix, tags):

    try:
        app.include_router(
            router,
            prefix=prefix,
            tags=tags,
        )

        print(f"Loaded : {prefix}")

    except Exception as e:
        print(f"Failed : {prefix} ---> {e}")


# ---------------------------------

try:
    register_router(
        auth.router,
        "/api/v1/auth",
        ["Auth"],
    )
except:
    pass

try:
    register_router(
        whatsapp.router,
        "/api/v1/whatsapp",
        ["WhatsApp"],
    )
except:
    pass

try:
    register_router(
        chat.router,
        "/api/v1/chat",
        ["Chat"],
    )
except:
    pass

try:
    register_router(
        stock.router,
        "/api/v1/stock",
        ["Stock"],
    )
except:
    pass

try:
    register_router(
        leads.router,
        "/api/v1/leads",
        ["Leads"],
    )
except:
    pass

try:
    register_router(
        appointments.router,
        "/api/v1/appointments",
        ["Appointments"],
    )
except:
    pass

try:
    register_router(
        analytics.router,
        "/api/v1/analytics",
        ["Analytics"],
    )
except:
    pass

try:
    register_router(
        dashboard.router,
        "/api/v1/dashboard",
        ["Dashboard"],
    )
except:
    pass

try:
    register_router(
        users.router,
        "/api/v1/users",
        ["Users"],
    )
except:
    pass

try:
    if stats_router:

        app.include_router(
            stats_router,
            prefix="/api/v1",
            tags=["Stats"],
        )

except Exception as e:
    print(f"Stats Router Error : {e}")


# -----------------------------------------------------
# Health APIs
# -----------------------------------------------------

@app.get("/")
async def root():

    return {
        "message": "AI WhatsApp Assistant API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "version": "/version",
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "app": getattr(
            settings,
            "APP_NAME",
            "AI WhatsApp Assistant",
        ),
        "environment": getattr(
            settings,
            "ENV",
            "production",
        ),
        "version": "1.0.0",
    }


@app.get("/version")
async def version():

    return {
        "version": "1.0.0"
    }


@app.get("/environment")
async def environment():

    return {
        "environment": getattr(
            settings,
            "ENV",
            "production",
        )
    }


# -----------------------------------------------------
# Global Exception Handler
# -----------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error": (
                str(exc)
                if getattr(settings, "DEBUG", False)
                else "Contact Support"
            ),
        },
    )


# -----------------------------------------------------
# Local Development
# -----------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            8000,
        )
    )

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
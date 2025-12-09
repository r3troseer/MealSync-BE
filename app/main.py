from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from .config import settings
from .database import get_db
from .core.middleware import ExceptionHandlingMiddleware
from .schemas.result import Result, Error, ErrorCategory

# Import routes
from .api.v1 import auth, user, households, meals, recipes, grocery_lists, ingredients, ai

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="MealSync API - Meal planning and grocery list management",
)

# Add exception handling middleware FIRST
app.add_middleware(ExceptionHandlingMiddleware, log_internal_errors=settings.DEBUG)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"]
)
app.include_router(user.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(
    households.router,
    prefix=f"{settings.API_V1_STR}/households",
    tags=["households"]
)
app.include_router(
    ingredients.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["ingredients"]
)
app.include_router(
    recipes.router,
    prefix=f"{settings.API_V1_STR}/recipes",
    tags=["recipes"]
)
app.include_router(
    meals.router,
    prefix=f"{settings.API_V1_STR}/meals",
    tags=["meals"]
)
app.include_router(
    grocery_lists.router,
    prefix=f"{settings.API_V1_STR}/grocery-lists",
    tags=["grocery-lists"]
)
# app.include_router(
#     ai.router,
#     prefix=f"{settings.API_V1_STR}/ai",
#     tags=["ai"]
# )


@app.get("/", response_model=Result[dict])
async def root():
    """Root endpoint with API information"""
    return Result.successful(
        data={
            "message": f"Welcome to {settings.PROJECT_NAME} API",
            "version": settings.VERSION,
            "docs": f"{settings.API_V1_STR}/docs",
            "status": "online",
        }
    )


@app.get("/health", response_model=Result[dict])
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for Railway and monitoring"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return Result.successful(data={"status": "healthy", "database": "connected"})
    except Exception as e:
        # Note: Exception will be caught by middleware
        # This is just for explicit health check response
        return Result.failure(
            error=Error(
                message=f"Health check failed: {str(e)}",
                status_code=503,
                category=ErrorCategory.INTERNAL,
            )
        )

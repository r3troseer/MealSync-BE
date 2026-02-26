from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from .config import settings
from .database import get_db
from .core.middleware import ExceptionHandlingMiddleware
from .schemas.result import Result, Error, ErrorCategory

# Import routes
from .api.v1 import (
    auth,
    user,
    households,
    meals,
    recipes,
    grocery_lists,
    ingredients,
    ai,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="MealSync API - Meal planning and grocery list management",
)


# Global exception handlers (catch exceptions before middleware)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic request validation errors and return Result format.
    This catches validation errors before they reach the middleware.
    """
    errors = exc.errors()
    error_messages = []

    for error in errors:
        # Skip 'body' prefix as it adds no useful context
        loc_parts = [str(x) for x in error["loc"] if x != "body"]
        loc = " -> ".join(loc_parts) if loc_parts else "request"
        msg = error["msg"]
        error_type = error.get("type", "")

        if error_type:
            error_messages.append(f"• {loc}: {msg} ({error_type})")
        else:
            error_messages.append(f"• {loc}: {msg}")

    readable_message = f"{len(error_messages)} validation error(s):\n" + "\n".join(error_messages)

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "message": readable_message,
                "status_code": 422,
                "category": "Validation",
            },
            "data": None,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Convert FastAPI HTTPExceptions to Result format.
    Ensures all HTTP exceptions follow the same response structure.
    """
    # Infer category from status code
    category_map = {
        400: "BadRequest",
        401: "Authentication",
        403: "Authorization",
        404: "NotFound",
        409: "ResourceConflict",
        422: "Validation",
    }
    category = category_map.get(exc.status_code, "Error")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code,
                "category": category,
            },
            "data": None,
        },
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
    households.router, prefix=f"{settings.API_V1_STR}/households", tags=["households"]
)
app.include_router(
    ingredients.router, prefix=f"{settings.API_V1_STR}", tags=["ingredients"]
)
app.include_router(
    recipes.router, prefix=f"{settings.API_V1_STR}/recipes", tags=["recipes"]
)
app.include_router(meals.router, prefix=f"{settings.API_V1_STR}/meals", tags=["meals"])
app.include_router(
    grocery_lists.router,
    prefix=f"{settings.API_V1_STR}/grocery-lists",
    tags=["grocery-lists"],
)
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["ai"])


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

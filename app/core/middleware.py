from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import WebSocketException
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import Sequence, Any

from schema.result import Error, Result, ErrorCategory
from exception import CustomException

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """
    Centralized exception handling middleware for consistent API responses.
    Catches all exceptions and transforms them into standardized Result objects.
    """

    # Map exception types to their handlers (initialized per instance)

    def __init__(self, app, log_internal_errors: bool = True):
        super().__init__(app)
        self.log_internal_errors = log_internal_errors
        self._register_handlers()

    def _register_handlers(self):
        """Register exception type to handler method mappings"""
        self.EXCEPTION_HANDLERS = {
            CustomException: self._handle_custom_exception,
            ValidationError: self._handle_validation_error,
            RequestValidationError: self._handle_validation_error,
            ResponseValidationError: self._handle_validation_error,
            HTTPException: self._handle_http_exception,
            WebSocketException: self._handle_websocket_exception,
        }

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as ex:
            return await self._handle_exception(ex, request)

    async def _handle_exception(self, ex: Exception, request: Request) -> JSONResponse:
        """
        Route exception to the appropriate handler.

        All registered handlers are expected to be asynchronous (async def).
        """
        # Check for specific exception types first
        for exc_type, handler in self.EXCEPTION_HANDLERS.items():
            if isinstance(ex, exc_type):
                return await handler(ex, request)

        # Default to internal server error
        return await self._handle_unhandled_exception(ex, request)

    async def _handle_custom_exception(
        self, ex: CustomException, request: Request
    ) -> JSONResponse:
        """Handle custom application exceptions"""
        error = Error(
            message=ex.detail, status_code=ex.status_code, category=ex.category
        )
        return self._create_error_response(error)

    async def _handle_validation_error(
        self,
        ex: ValidationError | RequestValidationError | ResponseValidationError,
        request: Request,
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
        validation_message = self._format_validation_error(ex.errors())
        error = Error(
            message=validation_message,
            status_code=422,
            category=ErrorCategory.VALIDATION,
        )
        return self._create_error_response(error)

    async def _handle_http_exception(
        self, ex: HTTPException, request: Request
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        # Infer category from status code
        category = self._infer_category_from_status(ex.status_code)

        error = Error(
            message=ex.detail if isinstance(ex.detail, str) else str(ex.detail),
            status_code=ex.status_code,
            category=category,
        )
        return self._create_error_response(error)

    async def _handle_websocket_exception(
        self, ex: WebSocketException, request: Request
    ) -> JSONResponse:
        """Handle WebSocket exceptions"""
        error = Error(
            message=str(ex.reason) if hasattr(ex, "reason") else str(ex),
            status_code=ex.code if hasattr(ex, "code") else 400,
            category=ErrorCategory.WEBSOCKET,
        )
        return self._create_error_response(error)

    async def _handle_unhandled_exception(
        self, ex: Exception, request: Request
    ) -> JSONResponse:
        """Handle unexpected exceptions"""
        if self.log_internal_errors:
            logger.error(
                f"Unhandled exception on {request.method} {request.url.path}",
                exc_info=ex,
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client": request.client.host if request.client else None,
                },
            )

        # Don't expose internal error details in production
        error = Error(
            message="An unexpected error occurred. Please try again later.",
            status_code=500,
            category=ErrorCategory.INTERNAL,
        )
        return self._create_error_response(error)

    def _create_error_response(self, error: Error) -> JSONResponse:
        """Create standardized JSON error response"""
        return JSONResponse(
            status_code=error.status_code, content=Result.failure(error).model_dump()
        )
    def _format_validation_error(self, errors: Sequence[Any]) -> str:
        """Format validation errors into human-readable message"""
        messages = []
        for error in errors:
            loc = " -> ".join(str(loc) for loc in error.get("loc", []))
            msg = error.get("msg", "Unknown error")
            error_type = error.get("type", "unknown")

            messages.append(f"Error in {loc}: {msg} (type: {error_type})")

        return "; ".join(messages) if messages else "Validation failed"

    def _infer_category_from_status(self, status_code: int) -> ErrorCategory:
        """Infer error category from HTTP status code"""
        status_category_map = {
            401: ErrorCategory.AUTHENTICATION,
            403: ErrorCategory.AUTHORIZATION,
            404: ErrorCategory.NOT_FOUND,
            409: ErrorCategory.RESOURCE_CONFLICT,
            422: ErrorCategory.VALIDATION,
        }
        if status_code in status_category_map:
            return status_category_map[status_code]
        elif 400 <= status_code < 500:
            return ErrorCategory.BAD_REQUEST
        elif status_code >= 500:
            return ErrorCategory.INTERNAL
        else:
            return ErrorCategory.CUSTOM

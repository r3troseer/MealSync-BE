from enum import Enum
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class ErrorCategory(Enum):
    VALIDATION = "Validation"
    NOT_FOUND = "Not Found"
    AUTHENTICATION = "Authentication"
    AUTHORIZATION = "Authorization"
    INTERNAL = "Internal Server Error"
    BAD_REQUEST = "Bad Request"
    RESOURCE_CONFLICT = "Resource Conflict"
    WEBSOCKET = "WebSocket Error"
    CUSTOM = "Custom Error"


class Error(BaseModel):
    message: str
    status_code: int
    category: ErrorCategory

    class Config:
        use_enum_values = True


class Result(BaseModel, Generic[T]):
    success: bool
    error: Optional[Error] = None
    data: Optional[T] = None

    @classmethod
    def successful(cls, data: Optional[T] = None):
        return cls(success=True, data=data)

    @classmethod
    def failure(cls, error: Error):
        return cls(success=False, error=error)

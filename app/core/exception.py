from fastapi import HTTPException
from typing import Any, Optional
from schema.result import ErrorCategory


class CustomException(HTTPException):
    """Base exception class for all custom application exceptions"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int, 
        category: ErrorCategory,
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.category = category


class ResourceNotFoundException(CustomException):
    """Exception raised when a requested resource is not found"""
    
    def __init__(self, resource_name: str, resource_id: Optional[Any] = None):
        if resource_id:
            message = f"{resource_name} with ID '{resource_id}' was not found."
        else:
            message = f"{resource_name} was not found."
        
        super().__init__(
            message=message,
            status_code=404,
            category=ErrorCategory.NOT_FOUND
        )


class AuthenticationException(CustomException):
    """Exception raised when authentication fails"""
    
    def __init__(self, message: str = "Invalid credentials. Access denied."):
        super().__init__(
            message=message,
            status_code=401,
            category=ErrorCategory.AUTHENTICATION,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(CustomException):
    """Exception raised when user lacks required permissions"""
    
    def __init__(
        self, 
        permission: Optional[str] = None, 
        message: Optional[str] = None,
        status_code: int = 403
    ):
        if message:
            error_message = message
        elif permission:
            error_message = f"You do not have permission to perform this action. Required permission: {permission}"
        else:
            error_message = "You do not have permission to perform this action."
        
        super().__init__(
            message=error_message,
            status_code=status_code,
            category=ErrorCategory.AUTHORIZATION
        )


class DuplicateResourceException(CustomException):
    """Exception raised when attempting to create a resource that already exists"""
    
    def __init__(
        self, 
        resource_name: str, 
        identifier: Optional[str] = None,
        status_code: int = 409
    ):
        if identifier:
            message = f"{resource_name} with identifier '{identifier}' already exists."
        else:
            message = f"{resource_name} already exists."
        
        super().__init__(
            message=message,
            status_code=status_code,
            category=ErrorCategory.RESOURCE_CONFLICT
        )


class ValidationException(CustomException):
    """Exception raised for business logic validation failures"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        if field:
            error_message = f"Validation failed for '{field}': {message}"
        else:
            error_message = f"Validation failed: {message}"
        
        super().__init__(
            message=error_message,
            status_code=422,
            category=ErrorCategory.VALIDATION
        )


class BadRequestException(CustomException):
    """Exception raised for malformed or invalid requests"""
    
    def __init__(self, message: str = "The request is invalid or malformed."):
        super().__init__(
            message=message,
            status_code=400,
            category=ErrorCategory.BAD_REQUEST
        )


class InternalServerException(CustomException):
    """Exception raised for internal server errors"""
    
    def __init__(self, message: str = "An internal server error occurred."):
        super().__init__(
            message=message,
            status_code=500,
            category=ErrorCategory.INTERNAL
        )
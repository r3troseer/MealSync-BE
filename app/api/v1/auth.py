from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas.user import UserCreate, UserResponse, Token
from ...schemas.result import Result
from ...services.authService import AuthService
from ...dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post(
    "/register",
    response_model=Result[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **email**: Valid email address (unique)
    - **username**: Username (unique, 3-50 chars)
    - **password**: Password (min 8 chars)
    - **full_name**: Optional full name
    - **dietary_preferences**: Optional dietary preferences
    - **allergies**: Optional allergies

    Returns:
        Result[UserResponse]: Success result with created user data
    """
    auth_service = AuthService(db)
    user = auth_service.register(user_data)
    return Result.successful(data=user)


@router.post("/swagger-login", response_model=Token)
async def swagger_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    token = service.login(form_data.username, form_data.password)
    return Token(
        access_token=token.access_token,
        token_type=token.token_type
    )


@router.post("/login", response_model=Result[Token])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Login with username/email and password.

    Returns access token and refresh token wrapped in Result.

    Returns:
        Result[Token]: Success result with access and refresh tokens
    """
    auth_service = AuthService(db)
    token = auth_service.login(form_data.username, form_data.password)
    return Result.successful(data=token)


@router.get("/me", response_model=Result[UserResponse])
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.

    Requires valid access token in Authorization header.

    Returns:
        Result[UserResponse]: Success result with current user data
    """
    return Result.successful(data=current_user)


@router.post("/refresh", response_model=Result[Token])
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        Result[Token]: Success result with new access token
    """
    auth_service = AuthService(db)
    new_token = auth_service.refresh_access_token(refresh_token)
    return Result.successful(data=new_token)


@router.post("/logout", response_model=Result[dict])
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user.

    Client should delete the token from storage.
    For token blacklisting, implement Redis-based solution.

    Returns:
        Result[dict]: Success result with logout message
    """
    return Result.successful(data={"message": "Successfully logged out"})

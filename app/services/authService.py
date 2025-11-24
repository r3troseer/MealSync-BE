from sqlalchemy.orm import Session
from datetime import timedelta
from ..models.user import User
from ..services.userService import UserService
from ..schemas.user import UserCreate, Token
from ..utils.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from ..config import settings
from ..core.exception import AuthenticationException, AuthorizationException


class AuthService:
    """Service layer for authentication operations."""

    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)

    def register(self, user_data: UserCreate) -> User:
        """
        Register a new user.
        Returns the created user.
        """
        return self.user_service.create_user(user_data)

    def login(self, username_or_email: str, password: str) -> Token:
        """
        Login user and return access token.
        """
        # Authenticate user
        user = self.user_service.authenticate_user(username_or_email, password)

        if not user:
            raise AuthenticationException("Incorrect username or password")

        # Check if user is active
        if not user.is_active:
            raise AuthorizationException(message="Account is deactivated")

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires,
        )

        # Create refresh token
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return Token(
            access_token=access_token, token_type="bearer", refresh_token=refresh_token
        )

    def refresh_access_token(self, refresh_token: str) -> Token:
        """
        Refresh access token using refresh token.
        Returns new access token.
        """
        payload = decode_access_token(refresh_token)

        # Validate refresh token
        if payload is None or payload.get("type") != "refresh":
            raise AuthenticationException("Could not validate refresh token")

        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise AuthenticationException("Invalid refresh token")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise AuthenticationException("Invalid token format")

        # Get user
        user = self.user_service.get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationException("Invalid user or inactive account")

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires,
        )

        return Token(access_token=new_access_token, token_type="bearer")

    def verify_token(self, token: str) -> User:
        """
        Verify token and return user.
        Raises HTTPException if token is invalid.
        """
        payload = decode_access_token(token)
        if payload is None:
            raise AuthenticationException("Could not validate credentials")

        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise AuthenticationException("Could not validate credentials")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise AuthenticationException("Invalid token format")

        user = self.user_service.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationException("User not found")

        if not user.is_active:
            raise AuthorizationException(message="Account is deactivated")

        return user

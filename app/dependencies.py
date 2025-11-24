from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .utils.security import decode_access_token
from app.models.user import User
from .config import settings
from .core.exception import AuthenticationException, ResourceNotFoundException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user.
    Raises CustomException instead of HTTPException for consistent error handling.

    Example:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}
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

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ResourceNotFoundException("User", user_id)

    if not user.is_active:
        raise AuthenticationException("Account is deactivated")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency for routes that require active users only.
    """
    if not current_user.is_active:
        raise AuthenticationException("Account is deactivated")
    return current_user

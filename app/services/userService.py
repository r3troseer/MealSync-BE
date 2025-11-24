from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from ..repositories.userRepository import UserRepository
from ..schemas.user import UserCreate, UserUpdate
from ..utils.security import get_password_hash, verify_password
from ..core.exception import (
    ResourceNotFoundException,
    DuplicateResourceException,
    BadRequestException,
)


class UserService:
    """Service layer for user operations."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.user_repo.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.user_repo.get_by_email(email)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.user_repo.get_by_username(username)

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Validates that username and email are unique.
        Hashes the password before storing.
        """
        # Check if username exists
        if self.user_repo.username_exists(user_data.username):
            raise DuplicateResourceException("User", user_data.username)

        # Check if email exists
        if self.user_repo.email_exists(user_data.email):
            raise DuplicateResourceException("User", user_data.email)

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Create user object
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            dietary_preferences=user_data.dietary_preferences,
            allergies=user_data.allergies,
            is_active=True,
            is_verified=False,
        )

        return self.user_repo.create(user)

    def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """Update user profile."""
        user = self.user_repo.get(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)

        # Only update provided fields
        update_data = user_data.model_dump(exclude_unset=True)

        updated_user = self.user_repo.update(user_id, update_data)

        if updated_user is None:
            raise ResourceNotFoundException("User", user_id)
        return updated_user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user account."""
        if not self.user_repo.delete(user_id):
            raise ResourceNotFoundException("User", user_id)
        return True

    def authenticate_user(
        self, username_or_email: str, password: str
    ) -> Optional[User]:
        """
        Authenticate a user by username/email and password.
        Returns User if credentials are valid, None otherwise.
        """
        user = self.user_repo.get_by_username_or_email(username_or_email)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> User:
        """Change user password."""
        user = self.user_repo.get(user_id)

        if not user:
            raise ResourceNotFoundException("User", user_id)

        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            raise BadRequestException("Old password is incorrect")

        # Hash and update new password
        hashed_password = get_password_hash(new_password)
        updated_user = self.user_repo.update_password(user_id, hashed_password)

        if updated_user is None:
            raise ResourceNotFoundException("User", user_id)
        return updated_user

    def deactivate_account(self, user_id: int) -> User:
        """Deactivate user account."""
        user = self.user_repo.deactivate_user(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)
        return user

    def get_all_users(self, skip: int = 0, limit: int = 100):
        """Get all users (admin only)."""
        return self.user_repo.get_all(skip=skip, limit=limit)

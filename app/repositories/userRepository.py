from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from ..repositories.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        """Get user by username or email (for login)."""
        return (
            self.db.query(User)
            .filter((User.username == identifier) | (User.email == identifier))
            .first()
        )

    def username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        return self.db.query(User).filter(User.username == username).count() > 0

    def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        return self.db.query(User).filter(User.email == email).count() > 0

    def get_active_users(self, skip: int = 0, limit: int = 100):
        """Get all active users."""
        return (
            self.db.query(User)
            .filter(User.is_active.is_(True))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_password(self, user_id: int, hashed_password: str) -> Optional[User]:
        """Update user password."""
        user = self.get(user_id)
        if user:
            user.hashed_password = hashed_password
            self.db.commit()
            self.db.refresh(user)
        return user

    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user account."""
        return self.update(user_id, {"is_active": False})

    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user account."""
        return self.update(user_id, {"is_active": True})

    def verify_email(self, user_id: int) -> Optional[User]:
        """Mark user email as verified."""
        return self.update(user_id, {"is_verified": True})

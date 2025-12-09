from sqlalchemy.orm import Session
from sqlalchemy import select, and_, insert, delete, update
from typing import List, Optional
from app.models.household import Household
from app.models.user import User
from app.models.associations import user_household
from app.repositories.repository import BaseRepository
import secrets
import string


class HouseholdRepository(BaseRepository[Household]):
    """Repository for household operations."""

    def __init__(self, db: Session):
        super().__init__(Household, db)

    def get_by_invite_code(self, code: str) -> Optional[Household]:
        """Find household by invite code."""
        return self.db.query(Household).filter(Household.invite_code == code).first()

    def get_user_households(self, user_id: int) -> List[Household]:
        """Get all households a user belongs to."""
        stmt = (
            select(Household)
            .join(user_household)
            .where(user_household.c.user_id == user_id)
            .order_by(Household.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def add_member(self, household_id: int, user_id: int, role: str = "member") -> bool:
        """
        Add a member to a household.

        Args:
            household_id: The household ID
            user_id: The user ID to add
            role: Role in the household ('admin' or 'member')

        Returns:
            True if successful, False if already a member
        """
        # Check if already a member
        if self.is_member(household_id, user_id):
            return False

        stmt = insert(user_household).values(
            user_id=user_id,
            household_id=household_id,
            role=role
        )
        self.db.execute(stmt)
        self.db.commit()
        return True

    def remove_member(self, household_id: int, user_id: int) -> bool:
        """
        Remove a member from a household.

        Returns:
            True if removed, False if not a member
        """
        if not self.is_member(household_id, user_id):
            return False

        stmt = delete(user_household).where(
            and_(
                user_household.c.household_id == household_id,
                user_household.c.user_id == user_id
            )
        )
        self.db.execute(stmt)
        self.db.commit()
        return True

    def get_members(self, household_id: int) -> List[dict]:
        """
        Get all members of a household with their roles.

        Returns:
            List of dicts with user info and role
        """
        stmt = (
            select(
                User.id,
                User.uuid,
                User.username,
                User.email,
                User.full_name,
                user_household.c.role,
                user_household.c.joined_at
            )
            .join(user_household, User.id == user_household.c.user_id)
            .where(user_household.c.household_id == household_id)
            .order_by(user_household.c.joined_at)
        )

        results = self.db.execute(stmt).all()
        return [
            {
                "user_id": r.id,
                "uuid": r.uuid,
                "username": r.username,
                "email": r.email,
                "full_name": r.full_name,
                "role": r.role,
                "joined_at": r.joined_at
            }
            for r in results
        ]

    def get_member_role(self, household_id: int, user_id: int) -> Optional[str]:
        """Get the role of a user in a household."""
        stmt = select(user_household.c.role).where(
            and_(
                user_household.c.household_id == household_id,
                user_household.c.user_id == user_id
            )
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def is_member(self, household_id: int, user_id: int) -> bool:
        """Check if a user is a member of a household."""
        stmt = select(user_household).where(
            and_(
                user_household.c.household_id == household_id,
                user_household.c.user_id == user_id
            )
        )
        return self.db.execute(stmt).first() is not None

    def is_admin(self, household_id: int, user_id: int) -> bool:
        """Check if a user is an admin of a household."""
        role = self.get_member_role(household_id, user_id)
        return role == "admin"

    def get_admin_count(self, household_id: int) -> int:
        """Get the number of admins in a household."""
        stmt = select(user_household).where(
            and_(
                user_household.c.household_id == household_id,
                user_household.c.role == "admin"
            )
        )
        return len(list(self.db.execute(stmt).all()))

    def promote_to_admin(self, household_id: int, user_id: int) -> bool:
        """Promote a member to admin."""
        if not self.is_member(household_id, user_id):
            return False

        stmt = (
            update(user_household)
            .where(
                and_(
                    user_household.c.household_id == household_id,
                    user_household.c.user_id == user_id
                )
            )
            .values(role="admin")
        )
        self.db.execute(stmt)
        self.db.commit()
        return True

    def generate_invite_code(self) -> str:
        """
        Generate a unique invite code.

        Returns:
            An 8-character alphanumeric code
        """
        while True:
            # Generate random 8-character alphanumeric code
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

            # Check if code already exists
            if not self.get_by_invite_code(code):
                return code

    def regenerate_invite_code(self, household_id: int) -> Optional[str]:
        """
        Generate a new invite code for a household.

        Returns:
            The new invite code, or None if household not found
        """
        household = self.get(household_id)
        if not household:
            return None

        new_code = self.generate_invite_code()
        self.update(household_id, {"invite_code": new_code})
        return new_code

    def get_member_count(self, household_id: int) -> int:
        """Get the number of members in a household."""
        stmt = select(user_household).where(user_household.c.household_id == household_id)
        return len(list(self.db.execute(stmt).all()))

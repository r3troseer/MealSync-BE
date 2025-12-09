from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.household import Household
from app.models.user import User
from app.repositories.household_repository import HouseholdRepository
from app.repositories.userRepository import UserRepository
from app.repositories.meal_repository import MealRepository
from app.schemas.household import (
    HouseholdCreate,
    HouseholdUpdate,
    HouseholdResponse,
    HouseholdMemberResponse,
    InviteCodeResponse
)
from app.core.exception import (
    ResourceNotFoundException,
    BadRequestException,
    AuthorizationException
)


class HouseholdService:
    """Service layer for household operations."""

    def __init__(self, db: Session):
        self.db = db
        self.household_repo = HouseholdRepository(db)
        self.user_repo = UserRepository(db)
        self.meal_repo = MealRepository(db)

    def create_household(self, user_id: int, data: HouseholdCreate) -> Household:
        """
        Create a new household with the user as admin.

        Args:
            user_id: ID of user creating the household
            data: Household creation data

        Returns:
            Created household
        """
        # Generate unique invite code
        invite_code = self.household_repo.generate_invite_code()

        # Create household
        household = Household(
            name=data.name,
            description=data.description,
            invite_code=invite_code,
            created_by_id=user_id
        )

        household = self.household_repo.create(household)

        # Add creator as admin member
        self.household_repo.add_member(household.id, user_id, role="admin")

        return household

    def get_user_households(self, user_id: int) -> List[Household]:
        """Get all households a user belongs to."""
        return self.household_repo.get_user_households(user_id)

    def get_household(self, household_id: int, user_id: int) -> Household:
        """
        Get household details.

        Args:
            household_id: Household ID
            user_id: Requesting user ID

        Returns:
            Household details

        Raises:
            AuthorizationException: If user is not a member
            ResourceNotFoundException: If household not found
        """
        household = self.household_repo.get(household_id)
        if not household:
            raise ResourceNotFoundException("Household", household_id)

        # Verify user is a member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You are not a member of this household")

        return household

    def update_household(self, household_id: int, user_id: int, data: HouseholdUpdate) -> Household:
        """
        Update household details.

        Args:
            household_id: Household ID
            user_id: Requesting user ID
            data: Update data

        Returns:
            Updated household

        Raises:
            AuthorizationException: If user is not an admin
            ResourceNotFoundException: If household not found
        """
        household = self.household_repo.get(household_id)
        if not household:
            raise ResourceNotFoundException("Household", household_id)

        # Verify user is admin
        if not self.household_repo.is_admin(household_id, user_id):
            raise AuthorizationException("Only admins can update household details")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        updated_household = self.household_repo.update(household_id, update_data)

        if not updated_household:
            raise ResourceNotFoundException("Household", household_id)

        return updated_household

    def delete_household(self, household_id: int, user_id: int) -> bool:
        """
        Delete a household (admin only).

        Cascade deletes all associated data (meals, recipes, grocery lists).

        Args:
            household_id: Household ID
            user_id: Requesting user ID

        Returns:
            True if deleted

        Raises:
            AuthorizationException: If user is not an admin
            ResourceNotFoundException: If household not found
        """
        household = self.household_repo.get(household_id)
        if not household:
            raise ResourceNotFoundException("Household", household_id)

        # Verify user is admin
        if not self.household_repo.is_admin(household_id, user_id):
            raise AuthorizationException("Only admins can delete the household")

        # Delete household (cascade will handle related data)
        return self.household_repo.delete(household_id)

    def join_household(self, user_id: int, invite_code: str) -> Household:
        """
        Join a household using an invite code.

        Args:
            user_id: User ID
            invite_code: Household invite code

        Returns:
            Household joined

        Raises:
            ResourceNotFoundException: If invite code invalid
            BadRequestException: If already a member
        """
        household = self.household_repo.get_by_invite_code(invite_code)
        if not household:
            raise ResourceNotFoundException("Household with invite code", invite_code)

        # Check if already a member
        if self.household_repo.is_member(household.id, user_id):
            raise BadRequestException("You are already a member of this household")

        # Add user as member
        self.household_repo.add_member(household.id, user_id, role="member")

        return household

    def leave_household(self, household_id: int, user_id: int, new_admin_id: Optional[int] = None) -> dict:
        """
        Leave a household.

        If user is the last admin, they must either:
        - Promote another member to admin (via new_admin_id)
        - Delete the household if they're the only member

        Args:
            household_id: Household ID
            user_id: User leaving
            new_admin_id: Optional user ID to promote to admin

        Returns:
            Dict with status message

        Raises:
            AuthorizationException: If not a member
            BadRequestException: If last admin without promotion
            ResourceNotFoundException: If household not found
        """
        household = self.household_repo.get(household_id)
        if not household:
            raise ResourceNotFoundException("Household", household_id)

        # Verify user is a member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You are not a member of this household")

        is_admin = self.household_repo.is_admin(household_id, user_id)
        admin_count = self.household_repo.get_admin_count(household_id)
        member_count = self.household_repo.get_member_count(household_id)

        # Check if last admin
        if is_admin and admin_count == 1:
            if member_count == 1:
                # Only member, delete household
                self.household_repo.delete(household_id)
                return {"message": "Household deleted as you were the only member"}

            # Must promote another admin
            if not new_admin_id:
                raise BadRequestException(
                    "You are the last admin. Please promote another member to admin before leaving."
                )

            # Validate new admin
            if not self.household_repo.is_member(household_id, new_admin_id):
                raise BadRequestException("New admin must be a household member")

            if new_admin_id == user_id:
                raise BadRequestException("Cannot promote yourself")

            # Promote new admin
            self.household_repo.promote_to_admin(household_id, new_admin_id)

        # Unassign user from all meals in this household
        self.meal_repo.unassign_user_from_household(household_id, user_id)

        # Remove user from household
        self.household_repo.remove_member(household_id, user_id)

        return {"message": "Successfully left household"}

    def get_members(self, household_id: int, user_id: int) -> List[dict]:
        """
        Get household members.

        Args:
            household_id: Household ID
            user_id: Requesting user ID

        Returns:
            List of members with roles

        Raises:
            AuthorizationException: If not a member
            ResourceNotFoundException: If household not found
        """
        household = self.household_repo.get(household_id)
        if not household:
            raise ResourceNotFoundException("Household", household_id)

        # Verify user is a member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You are not a member of this household")

        return self.household_repo.get_members(household_id)

    def remove_member(self, household_id: int, admin_id: int, member_id: int) -> dict:
        """
        Remove a member from the household (admin only).

        Args:
            household_id: Household ID
            admin_id: Admin user ID
            member_id: Member to remove

        Returns:
            Dict with status message

        Raises:
            AuthorizationException: If requester is not an admin
            BadRequestException: If trying to remove self or last admin
            ResourceNotFoundException: If household not found
        """
        household = self.household_repo.get(household_id)
        if not household:
            raise ResourceNotFoundException("Household", household_id)

        # Verify requester is admin
        if not self.household_repo.is_admin(household_id, admin_id):
            raise AuthorizationException("Only admins can remove members")

        # Cannot remove self (use leave instead)
        if admin_id == member_id:
            raise BadRequestException("Use leave endpoint to remove yourself")

        # Check if member is admin
        is_member_admin = self.household_repo.is_admin(household_id, member_id)
        if is_member_admin:
            admin_count = self.household_repo.get_admin_count(household_id)
            if admin_count == 1:
                raise BadRequestException("Cannot remove the last admin")

        # Unassign from meals
        self.meal_repo.unassign_user_from_household(household_id, member_id)

        # Remove member
        success = self.household_repo.remove_member(household_id, member_id)
        if not success:
            raise BadRequestException("User is not a member of this household")

        return {"message": "Member removed successfully"}

    def regenerate_invite_code(self, household_id: int, user_id: int) -> str:
        """
        Generate a new invite code for the household.

        Args:
            household_id: Household ID
            user_id: Requesting user ID

        Returns:
            New invite code

        Raises:
            AuthorizationException: If not an admin
            ResourceNotFoundException: If household not found
        """
        household = self.household_repo.get(household_id)
        if not household:
            raise ResourceNotFoundException("Household", household_id)

        # Verify user is admin
        if not self.household_repo.is_admin(household_id, user_id):
            raise AuthorizationException("Only admins can regenerate invite codes")

        new_code = self.household_repo.regenerate_invite_code(household_id)
        if not new_code:
            raise ResourceNotFoundException("Household", household_id)

        return new_code

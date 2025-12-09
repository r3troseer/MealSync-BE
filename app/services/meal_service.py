from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
from app.models.meal import Meal, MealStatus
from app.repositories.meal_repository import MealRepository
from app.repositories.household_repository import HouseholdRepository
from app.repositories.recipe_repository import RecipeRepository
from app.schemas.meal import MealCreate, MealUpdate, MealDateRangeParams
from app.core.exception import (
    ResourceNotFoundException,
    BadRequestException,
    AuthorizationException
)


class MealService:
    """Service layer for meal operations."""

    def __init__(self, db: Session):
        self.db = db
        self.meal_repo = MealRepository(db)
        self.household_repo = HouseholdRepository(db)
        self.recipe_repo = RecipeRepository(db)

    def create_meal(self, user_id: int, data: MealCreate) -> Meal:
        """
        Create a new meal.

        Args:
            user_id: User creating the meal
            data: Meal creation data

        Returns:
            Created meal

        Raises:
            AuthorizationException: If user not member of household
            BadRequestException: If recipe invalid or date in past
        """
        # Verify user is member of household
        if not self.household_repo.is_member(data.household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Verify recipe exists and belongs to household (if provided)
        if data.recipe_id:
            recipe = self.recipe_repo.get(data.recipe_id)
            if not recipe or recipe.household_id != data.household_id:
                raise BadRequestException("Recipe not found or doesn't belong to this household")

        # Verify assigned user is member (if provided)
        if data.assigned_to_id:
            if not self.household_repo.is_member(data.household_id, data.assigned_to_id):
                raise BadRequestException("Assigned user must be a household member")

        # Create meal
        meal = Meal(**data.model_dump(), status=MealStatus.PLANNED)
        return self.meal_repo.create(meal)

    def get_meal(self, meal_id: int, user_id: int) -> Meal:
        """Get meal details."""
        meal = self.meal_repo.get(meal_id)
        if not meal:
            raise ResourceNotFoundException("Meal", meal_id)

        # Verify user is member
        if not self.household_repo.is_member(meal.household_id, user_id):
            raise AuthorizationException("You don't have access to this meal")

        return meal

    def update_meal(self, meal_id: int, user_id: int, data: MealUpdate) -> Meal:
        """Update a meal."""
        meal = self.meal_repo.get(meal_id)
        if not meal:
            raise ResourceNotFoundException("Meal", meal_id)

        # Verify user is member
        if not self.household_repo.is_member(meal.household_id, user_id):
            raise AuthorizationException("You don't have permission to update this meal")

        # Validate recipe if being updated
        if data.recipe_id is not None:
            recipe = self.recipe_repo.get(data.recipe_id)
            if not recipe or recipe.household_id != meal.household_id:
                raise BadRequestException("Recipe not found or doesn't belong to this household")

        # Update meal
        update_data = data.model_dump(exclude_unset=True)
        updated_meal = self.meal_repo.update(meal_id, update_data)

        if not updated_meal:
            raise ResourceNotFoundException("Meal", meal_id)

        return updated_meal

    def delete_meal(self, meal_id: int, user_id: int) -> dict:
        """Delete a meal."""
        meal = self.meal_repo.get(meal_id)
        if not meal:
            raise ResourceNotFoundException("Meal", meal_id)

        # Verify user is member
        if not self.household_repo.is_member(meal.household_id, user_id):
            raise AuthorizationException("You don't have permission to delete this meal")

        # Delete meal (grocery list items will remain)
        self.meal_repo.delete(meal_id)

        return {"message": "Meal deleted successfully"}

    def assign_meal(self, meal_id: int, user_id: int, assignee_id: int) -> Meal | None:
        """Assign a meal to a user."""
        meal = self.meal_repo.get(meal_id)
        if not meal:
            raise ResourceNotFoundException("Meal", meal_id)

        # Verify requester is member
        if not self.household_repo.is_member(meal.household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Verify assignee is member
        if not self.household_repo.is_member(meal.household_id, assignee_id):
            raise BadRequestException("Assignee must be a household member")

        # Assign meal
        updated_meal = self.meal_repo.assign_to_user(meal_id, assignee_id)

        # Update status to preparing if it was planned
        if updated_meal and updated_meal.status == MealStatus.PLANNED:
            updated_meal = self.meal_repo.update_status(meal_id, MealStatus.PREPARING)

        return updated_meal

    def claim_meal(self, meal_id: int, user_id: int) -> Meal | None:
        """Claim a meal (assign to self)."""
        return self.assign_meal(meal_id, user_id, user_id)

    def unclaim_meal(self, meal_id: int, user_id: int) -> Meal | None:
        """Unclaim a meal (remove assignment)."""
        meal = self.meal_repo.get(meal_id)
        if not meal:
            raise ResourceNotFoundException("Meal", meal_id)

        # Verify user is assigned to this meal
        if meal.assigned_to_id != user_id:
            raise AuthorizationException("You are not assigned to this meal")

        # Unassign
        updated_meal = self.meal_repo.assign_to_user(meal_id, None)

        # Reset status to planned
        if updated_meal:
            updated_meal = self.meal_repo.update_status(meal_id, MealStatus.PLANNED)

        return updated_meal

    def get_meals_by_date_range(
        self,
        household_id: int,
        user_id: int,
        params: MealDateRangeParams
    ) -> List[Meal]:
        """Get meals within a date range."""
        # Verify user is member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        return self.meal_repo.get_by_date_range(
            household_id=household_id,
            start_date=params.start_date,
            end_date=params.end_date,
            meal_type=params.meal_type,
            status=params.status,
            assigned_only=params.assigned_only
        )

    def get_weekly_meal_plan(self, household_id: int, user_id: int, week_start: date) -> dict:
        """Get weekly meal plan grouped by day and meal type."""
        # Verify user is member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        meals = self.meal_repo.get_weekly_plan(household_id, week_start)

        # Group by date and meal type
        meals_by_day = {}
        for meal in meals:
            date_key = meal.meal_date.isoformat()
            if date_key not in meals_by_day:
                meals_by_day[date_key] = {}

            meal_type_key = meal.meal_type.value
            if meal_type_key not in meals_by_day[date_key]:
                meals_by_day[date_key][meal_type_key] = []

            meals_by_day[date_key][meal_type_key].append(meal)

        return {
            "week_start": week_start,
            "week_end": week_start + timedelta(days=6),
            "meals_by_day": meals_by_day,
            "total_meals": len(meals)
        }

    def get_meal_calendar(self, household_id: int, user_id: int, month: int, year: int) -> List[Meal]:
        """Get meal calendar for a specific month."""
        # Verify user is member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        return self.meal_repo.get_calendar_view(household_id, month, year)

    def update_meal_status(self, meal_id: int, user_id: int, status: MealStatus) -> Meal | None:
        """Update meal status."""
        meal = self.meal_repo.get(meal_id)
        if not meal:
            raise ResourceNotFoundException("Meal", meal_id)

        # Verify user is member (or assigned for stricter control)
        if not self.household_repo.is_member(meal.household_id, user_id):
            raise AuthorizationException("You don't have permission to update this meal")

        # Update status
        updated_meal = self.meal_repo.update_status(meal_id, status)
        return updated_meal

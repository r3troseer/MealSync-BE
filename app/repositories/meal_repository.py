from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, extract
from typing import List, Optional
from datetime import date, timedelta
from app.models.meal import Meal, MealType, MealStatus
from app.repositories.repository import BaseRepository


class MealRepository(BaseRepository[Meal]):
    """Repository for meal operations."""

    def __init__(self, db: Session):
        super().__init__(Meal, db)

    def get_by_household(self, household_id: int, skip: int = 0, limit: int = 100) -> List[Meal]:
        """Get all meals for a household."""
        return (
            self.db.query(Meal)
            .filter(Meal.household_id == household_id)
            .order_by(Meal.meal_date.desc(), Meal.meal_type)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_date_range(
        self,
        household_id: int,
        start_date: date,
        end_date: date,
        meal_type: Optional[MealType] = None,
        status: Optional[MealStatus] = None,
        assigned_only: bool = False
    ) -> List[Meal]:
        """
        Get meals within a date range.

        Args:
            household_id: Household ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            meal_type: Optional filter by meal type
            status: Optional filter by status
            assigned_only: If True, only return assigned meals
        """
        filters = [
            Meal.household_id == household_id,
            Meal.meal_date >= start_date,
            Meal.meal_date <= end_date
        ]

        if meal_type:
            filters.append(Meal.meal_type == meal_type)

        if status:
            filters.append(Meal.status == status)

        if assigned_only:
            filters.append(Meal.assigned_to_id.isnot(None))

        return (
            self.db.query(Meal)
            .filter(and_(*filters))
            .order_by(Meal.meal_date, Meal.meal_type)
            .all()
        )

    def get_weekly_plan(self, household_id: int, week_start: date) -> List[Meal]:
        """
        Get 7-day meal plan starting from a specific date.

        Args:
            household_id: Household ID
            week_start: Start date of the week
        """
        week_end = week_start + timedelta(days=6)
        return self.get_by_date_range(household_id, week_start, week_end)

    def get_calendar_view(self, household_id: int, month: int, year: int) -> List[Meal]:
        """
        Get all meals for a specific month.

        Args:
            household_id: Household ID
            month: Month (1-12)
            year: Year
        """
        return (
            self.db.query(Meal)
            .filter(
                and_(
                    Meal.household_id == household_id,
                    extract('month', Meal.meal_date) == month,
                    extract('year', Meal.meal_date) == year
                )
            )
            .order_by(Meal.meal_date, Meal.meal_type)
            .all()
        )

    def get_by_user(self, household_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[Meal]:
        """Get meals assigned to a specific user."""
        return (
            self.db.query(Meal)
            .filter(
                and_(
                    Meal.household_id == household_id,
                    Meal.assigned_to_id == user_id
                )
            )
            .order_by(Meal.meal_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def assign_to_user(self, meal_id: int, user_id: Optional[int]) -> Optional[Meal]:
        """
        Assign a meal to a user (or unassign if user_id is None).

        Returns:
            Updated meal or None if not found
        """
        meal = self.get(meal_id)
        if not meal:
            return None

        meal.assigned_to_id = user_id
        self.db.commit()
        self.db.refresh(meal)
        return meal

    def update_status(self, meal_id: int, status: MealStatus) -> Optional[Meal]:
        """
        Update meal status.

        Returns:
            Updated meal or None if not found
        """
        meal = self.get(meal_id)
        if not meal:
            return None

        meal.status = status
        self.db.commit()
        self.db.refresh(meal)
        return meal

    def get_meals_by_recipe(self, recipe_id: int) -> List[Meal]:
        """Get all meals using a specific recipe."""
        return self.db.query(Meal).filter(Meal.recipe_id == recipe_id).all()

    def unassign_user_from_household(self, household_id: int, user_id: int) -> int:
        """
        Unassign a user from all meals in a household.

        Returns:
            Number of meals updated
        """
        meals = (
            self.db.query(Meal)
            .filter(
                and_(
                    Meal.household_id == household_id,
                    Meal.assigned_to_id == user_id
                )
            )
            .all()
        )

        count = len(meals)
        for meal in meals:
            meal.assigned_to_id = None

        self.db.commit()
        return count

    def get_upcoming_meals(self, household_id: int, days: int = 7) -> List[Meal]:
        """
        Get upcoming meals for the next N days.

        Args:
            household_id: Household ID
            days: Number of days to look ahead (default 7)
        """
        today = date.today()
        end_date = today + timedelta(days=days)

        return (
            self.db.query(Meal)
            .filter(
                and_(
                    Meal.household_id == household_id,
                    Meal.meal_date >= today,
                    Meal.meal_date <= end_date,
                    Meal.status.in_([MealStatus.PLANNED, MealStatus.PREPARING])
                )
            )
            .order_by(Meal.meal_date, Meal.meal_type)
            .all()
        )

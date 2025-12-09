from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.meal import MealStatus
from app.schemas.meal import (
    MealCreate,
    MealUpdate,
    MealResponse,
    MealAssign,
    MealStatusUpdate,
    MealCalendarResponse,
    WeeklyMealPlanResponse,
    MealDateRangeParams
)
from app.schemas.result import Result
from app.services.meal_service import MealService

router = APIRouter()


@router.post("", response_model=Result[MealResponse], status_code=status.HTTP_201_CREATED)
async def create_meal(
    meal_data: MealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new meal."""
    service = MealService(db)
    meal = service.create_meal(current_user.id, meal_data)
    return Result.successful(data=meal)


@router.get("", response_model=Result[List[MealResponse]])
async def get_meals(
    household_id: int = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    meal_type: str = Query(None),
    status: MealStatus = Query(None),
    assigned_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get meals by date range with optional filters."""
    from app.schemas.meal import MealDateRangeParams
    from app.models.meal import MealType

    params = MealDateRangeParams(
        start_date=start_date,
        end_date=end_date,
        meal_type=MealType(meal_type) if meal_type else None,
        status=status,
        assigned_only=assigned_only
    )

    service = MealService(db)
    meals = service.get_meals_by_date_range(household_id, current_user.id, params)
    return Result.successful(data=meals)


@router.get("/{meal_id}", response_model=Result[MealResponse])
async def get_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get meal details."""
    service = MealService(db)
    meal = service.get_meal(meal_id, current_user.id)
    return Result.successful(data=meal)


@router.put("/{meal_id}", response_model=Result[MealResponse])
async def update_meal(
    meal_id: int,
    meal_data: MealUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update meal details."""
    service = MealService(db)
    meal = service.update_meal(meal_id, current_user.id, meal_data)
    return Result.successful(data=meal)


@router.delete("/{meal_id}", response_model=Result[dict])
async def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a meal."""
    service = MealService(db)
    result = service.delete_meal(meal_id, current_user.id)
    return Result.successful(data=result)


@router.post("/{meal_id}/assign", response_model=Result[MealResponse])
async def assign_meal(
    meal_id: int,
    assign_data: MealAssign,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a meal to a user."""
    service = MealService(db)
    meal = service.assign_meal(meal_id, current_user.id, assign_data.assigned_to_id)
    return Result.successful(data=meal)


@router.post("/{meal_id}/claim", response_model=Result[MealResponse])
async def claim_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Claim a meal (assign to yourself)."""
    service = MealService(db)
    meal = service.claim_meal(meal_id, current_user.id)
    return Result.successful(data=meal)


@router.post("/{meal_id}/unclaim", response_model=Result[MealResponse])
async def unclaim_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unclaim a meal (remove assignment)."""
    service = MealService(db)
    meal = service.unclaim_meal(meal_id, current_user.id)
    return Result.successful(data=meal)


@router.patch("/{meal_id}/status", response_model=Result[MealResponse])
async def update_status(
    meal_id: int,
    status_data: MealStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update meal status."""
    service = MealService(db)
    meal = service.update_meal_status(meal_id, current_user.id, status_data.status)
    return Result.successful(data=meal)


@router.get("/households/{household_id}/meals/week", response_model=Result[WeeklyMealPlanResponse])
async def get_weekly_plan(
    household_id: int,
    week_start: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get weekly meal plan grouped by day and meal type."""
    service = MealService(db)
    plan = service.get_weekly_meal_plan(household_id, current_user.id, week_start)
    return Result.successful(data=plan)


@router.get("/households/{household_id}/meals/calendar", response_model=Result[List[MealCalendarResponse]])
async def get_calendar(
    household_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get meal calendar for a specific month."""
    service = MealService(db)
    meals = service.get_meal_calendar(household_id, current_user.id, month, year)
    return Result.successful(data=meals)

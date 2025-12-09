from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import date, datetime
from app.models.meal import MealType, MealStatus


class MealBase(BaseModel):
    """Base meal schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Meal name")
    meal_type: MealType = Field(..., description="Type of meal")
    meal_date: date = Field(..., description="Date when meal is scheduled")
    notes: Optional[str] = Field(None, max_length=500, description="Meal notes")
    servings: int = Field(1, ge=1, le=100, description="Number of servings")

    @field_validator('meal_date')
    @classmethod
    def validate_meal_date(cls, v: date) -> date:
        """Validate that meal date is not in the past."""
        if v < date.today():
            raise ValueError('Meal date cannot be in the past')
        return v


class MealCreate(MealBase):
    """Schema for creating a new meal."""
    household_id: int = Field(..., description="Household ID")
    recipe_id: Optional[int] = Field(None, description="Recipe ID (optional)")
    assigned_to_id: Optional[int] = Field(None, description="User ID assigned to cook (optional)")


class MealUpdate(BaseModel):
    """Schema for updating meal details."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    meal_type: Optional[MealType] = None
    meal_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)
    servings: Optional[int] = Field(None, ge=1, le=100)
    status: Optional[MealStatus] = None
    recipe_id: Optional[int] = None

    @field_validator('meal_date')
    @classmethod
    def validate_meal_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate that meal date is not in the past."""
        if v is not None and v < date.today():
            raise ValueError('Meal date cannot be in the past')
        return v


class MealAssign(BaseModel):
    """Schema for assigning a meal to a user."""
    assigned_to_id: int = Field(..., description="User ID to assign the meal to")


class MealStatusUpdate(BaseModel):
    """Schema for updating meal status."""
    status: MealStatus = Field(..., description="New meal status")


class MealResponse(MealBase):
    """Schema for meal response with full details."""
    id: int
    uuid: str
    household_id: int
    recipe_id: Optional[int]
    assigned_to_id: Optional[int]
    status: MealStatus
    created_at: datetime
    updated_at: Optional[datetime]

    # Expanded details
    recipe_name: Optional[str] = None
    assignee_name: Optional[str] = None
    is_assigned: bool = False
    has_recipe: bool = False

    class Config:
        from_attributes = True


class MealCalendarResponse(BaseModel):
    """Simplified schema for calendar view."""
    id: int
    uuid: str
    name: str
    meal_type: MealType
    meal_date: date
    status: MealStatus
    recipe_name: Optional[str] = None
    assignee_name: Optional[str] = None

    class Config:
        from_attributes = True


class WeeklyMealPlanResponse(BaseModel):
    """Schema for weekly meal plan grouped by day and meal type."""
    week_start: date
    week_end: date
    meals_by_day: Dict[str, Dict[str, List[MealCalendarResponse]]] = Field(
        ...,
        description="Meals grouped by date (ISO format) and meal type"
    )
    total_meals: int = Field(..., description="Total number of meals in the week")


class MealDateRangeParams(BaseModel):
    """Schema for meal date range query parameters."""
    start_date: date = Field(..., description="Start date for meal query")
    end_date: date = Field(..., description="End date for meal query")
    meal_type: Optional[MealType] = Field(None, description="Filter by meal type")
    status: Optional[MealStatus] = Field(None, description="Filter by status")
    assigned_only: bool = Field(False, description="Show only assigned meals")

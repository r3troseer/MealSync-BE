from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

from app.models.ingredient import UnitOfMeasurement, IngredientCategory
from app.models.recipe import DifficultyLevel, CuisineType
from app.models.meal import MealType


# ===== Generate Ingredients Schemas =====


class GenerateIngredientsRequest(BaseModel):
    """Request to generate ingredients from meal name"""

    meal_name: str = Field(..., min_length=1, max_length=200)
    servings: int = Field(4, ge=1, le=100)
    dietary_restrictions: Optional[List[str]] = Field(
        None, description="e.g., vegetarian, gluten-free, vegan"
    )
    household_id: int = Field(
        ..., description="Household context for ingredient matching"
    )


class GeneratedIngredient(BaseModel):
    """AI-generated ingredient with matching info"""

    name: str
    quantity: float
    unit: UnitOfMeasurement
    category: IngredientCategory
    notes: Optional[str] = None
    existing_ingredient_id: Optional[int] = Field(
        None, description="Matched household ingredient ID"
    )
    is_new: bool = Field(False, description="Needs to be created")
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Matching confidence 0-1"
    )


class GenerateIngredientsResponse(BaseModel):
    """Response with generated ingredients"""

    meal_name: str
    household_id: int
    ingredients: List[GeneratedIngredient]
    total_ingredients: int
    new_ingredients_count: int
    matched_ingredients_count: int


# ===== Generate Recipe Schemas =====


class GenerateRecipeRequest(BaseModel):
    """Request to generate recipe from meal name and optional ingredients"""

    meal_name: str = Field(..., min_length=1, max_length=200)
    ingredient_ids: Optional[List[int]] = Field(
        None, description="Optional household ingredient IDs to use (AI will suggest all ingredients if not provided)"
    )
    household_id: int
    servings: int = Field(4, ge=1, le=100)
    difficulty: Optional[DifficultyLevel] = None
    max_prep_time_minutes: Optional[int] = Field(None, ge=0, le=999)
    cuisine_type: Optional[CuisineType] = None
    dietary_restrictions: Optional[List[str]] = None


class GeneratedRecipeIngredient(BaseModel):
    """Ingredient usage in generated recipe"""

    ingredient_id: Optional[int] = Field(
        None, description="Household ingredient ID (null if new)"
    )
    ingredient_name: str
    quantity: float
    unit: UnitOfMeasurement
    category: Optional[IngredientCategory] = None
    notes: Optional[str] = None
    is_optional: bool = False
    is_new: bool = Field(False, description="True if ingredient needs to be created")
    is_user_provided: bool = Field(
        False, description="True if from user's selected ingredients"
    )


class GenerateRecipeResponse(BaseModel):
    """Response with generated recipe (not yet saved)"""

    name: str
    description: Optional[str]
    instructions: str
    prep_time_minutes: Optional[int]
    cook_time_minutes: Optional[int]
    servings: int
    difficulty: Optional[DifficultyLevel]
    cuisine_type: Optional[CuisineType]
    tags: Optional[str]
    calories_per_serving: Optional[int]
    ingredients: List[GeneratedRecipeIngredient]
    household_id: int  # Added for save operation

    # Meta info
    ai_generated: bool = True
    requires_user_approval: bool = True


# ===== Generate Meal Plan Schemas =====


class GenerateMealPlanRequest(BaseModel):
    """Request to generate meal plan from available ingredients"""

    household_id: int
    days: int = Field(7, ge=1, le=30, description="Number of days to plan")
    meals_per_day: int = Field(3, ge=1, le=6, description="Meals per day")
    start_date: Optional[date] = Field(None, description="Start date for meal plan")
    dietary_preferences: Optional[List[str]] = None
    use_available_only: bool = Field(
        False, description="Only use ingredients in inventory"
    )
    preferred_meal_types: Optional[List[MealType]] = Field(
        None, description="breakfast, lunch, dinner, snack"
    )


class GeneratedMealSuggestion(BaseModel):
    """Single meal suggestion in the plan"""

    day: int
    meal_date: Optional[date] = None
    meal_type: MealType
    meal_name: str
    description: Optional[str] = None
    ingredients_used: List[str] = Field(
        ..., description="Ingredient names from available"
    )
    additional_ingredients_needed: List[str] = Field(default_factory=list)
    estimated_prep_time_minutes: Optional[int] = None
    estimated_calories: Optional[int] = None

    # Ingredient matching
    matched_ingredient_ids: List[int] = Field(default_factory=list)
    requires_shopping: bool = Field(False, description="Needs additional ingredients")


class GenerateMealPlanResponse(BaseModel):
    """Response with generated meal plan suggestions"""

    household_id: int
    start_date: date
    end_date: date
    total_days: int
    meal_suggestions: List[GeneratedMealSuggestion]
    total_meals: int

    # Summary stats
    available_ingredients_count: int
    meals_with_all_ingredients: int
    meals_requiring_shopping: int

    ai_generated: bool = True
    requires_user_approval: bool = True

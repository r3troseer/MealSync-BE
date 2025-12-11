from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from app.models.recipe import DifficultyLevel, CuisineType
from app.models.ingredient import UnitOfMeasurement, IngredientCategory


class RecipeIngredientCreate(BaseModel):
    """Schema for creating a recipe ingredient."""
    ingredient_id: Optional[int] = Field(None, gt=0, description="Existing ingredient ID, or None for auto-create")
    ingredient_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Required if ingredient_id is None")
    ingredient_category: Optional[IngredientCategory] = Field(None, description="Category for new ingredients")
    quantity: float = Field(..., gt=0, description="Quantity needed")
    unit: UnitOfMeasurement = Field(..., description="Unit of measurement")
    notes: Optional[str] = Field(None, max_length=200, description="Preparation notes (e.g., 'chopped', 'diced')")
    is_optional: bool = Field(False, description="Whether this ingredient is optional")
    order: Optional[int] = Field(None, description="Display order in recipe")

    @model_validator(mode='after')
    def validate_ingredient(self):
        """Either ingredient_id or ingredient_name must be provided"""
        if self.ingredient_id is None and self.ingredient_name is None:
            raise ValueError("Either ingredient_id or ingredient_name must be provided")
        return self


class RecipeIngredientResponse(BaseModel):
    """Schema for recipe ingredient response with ingredient details."""
    id: int
    uuid: str
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: UnitOfMeasurement
    notes: Optional[str]
    is_optional: bool
    order: Optional[int]
    category: Optional[str] = None

    class Config:
        from_attributes = True


class RecipeBase(BaseModel):
    """Base recipe schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Recipe name")
    description: Optional[str] = Field(None, description="Recipe description")
    instructions: str = Field(..., min_length=1, max_length=5000, description="Cooking instructions")
    prep_time_minutes: Optional[int] = Field(None, ge=0, le=999, description="Preparation time in minutes")
    cook_time_minutes: Optional[int] = Field(None, ge=0, le=999, description="Cooking time in minutes")
    servings: int = Field(..., ge=1, le=100, description="Number of servings")
    difficulty: Optional[DifficultyLevel] = Field(None, description="Recipe difficulty")
    cuisine_type: Optional[CuisineType] = Field(None, description="Cuisine type")
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags")
    calories_per_serving: Optional[int] = Field(None, ge=0, description="Calories per serving")
    source_url: Optional[str] = Field(None, max_length=500, description="Recipe source URL")
    image_url: Optional[str] = Field(None, max_length=500, description="Recipe image URL")
    is_public: bool = Field(False, description="Whether recipe is public")


class RecipeCreate(RecipeBase):
    """Schema for creating a new recipe."""
    household_id: int = Field(..., description="Household ID")
    ingredients: List[RecipeIngredientCreate] = Field(..., min_length=1, description="List of ingredients")


class RecipeUpdate(BaseModel):
    """Schema for updating recipe details."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = Field(None, min_length=1, max_length=5000)
    prep_time_minutes: Optional[int] = Field(None, ge=0, le=999)
    cook_time_minutes: Optional[int] = Field(None, ge=0, le=999)
    servings: Optional[int] = Field(None, ge=1, le=100)
    difficulty: Optional[DifficultyLevel] = None
    cuisine_type: Optional[CuisineType] = None
    tags: Optional[str] = Field(None, max_length=500)
    calories_per_serving: Optional[int] = Field(None, ge=0)
    source_url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    ingredients: Optional[List[RecipeIngredientCreate]] = Field(None, description="Update ingredients list")


class RecipeResponse(RecipeBase):
    """Schema for recipe response with full details."""
    id: int
    uuid: str
    household_id: Optional[int]
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    total_time_minutes: Optional[int] = None
    ingredients: List[RecipeIngredientResponse] = []
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class RecipeSearchParams(BaseModel):
    """Schema for recipe search parameters."""
    query: Optional[str] = Field(None, min_length=1, description="Search query for recipe name")
    cuisine_type: Optional[CuisineType] = Field(None, description="Filter by cuisine type")
    difficulty: Optional[DifficultyLevel] = Field(None, description="Filter by difficulty")
    min_prep_time: Optional[int] = Field(None, ge=0, description="Minimum prep time in minutes")
    max_prep_time: Optional[int] = Field(None, ge=0, description="Maximum prep time in minutes")
    min_cook_time: Optional[int] = Field(None, ge=0, description="Minimum cook time in minutes")
    max_cook_time: Optional[int] = Field(None, ge=0, description="Maximum cook time in minutes")
    ingredient_ids: Optional[List[int]] = Field(None, description="Filter by ingredient IDs (must contain all)")
    tags: Optional[str] = Field(None, description="Filter by tags (comma-separated)")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")

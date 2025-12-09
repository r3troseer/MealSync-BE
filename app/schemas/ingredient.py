from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.ingredient import IngredientCategory, UnitOfMeasurement


class IngredientBase(BaseModel):
    """Base ingredient schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Ingredient name")
    category: Optional[IngredientCategory] = Field(None, description="Ingredient category")
    description: Optional[str] = Field(None, max_length=500, description="Ingredient description")
    average_price: Optional[float] = Field(None, ge=0, description="Average price")
    price_unit: Optional[UnitOfMeasurement] = Field(None, description="Price unit of measurement")


class IngredientCreate(IngredientBase):
    """Schema for creating a new ingredient."""
    household_id: int = Field(..., description="Household ID")


class IngredientUpdate(BaseModel):
    """Schema for updating ingredient details."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[IngredientCategory] = None
    description: Optional[str] = Field(None, max_length=500)
    average_price: Optional[float] = Field(None, ge=0)
    price_unit: Optional[UnitOfMeasurement] = None


class IngredientResponse(IngredientBase):
    """Schema for ingredient response."""
    id: int
    uuid: str
    household_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class IngredientSearchParams(BaseModel):
    """Schema for ingredient search parameters."""
    query: Optional[str] = Field(None, min_length=1, description="Search query for ingredient name")
    category: Optional[IngredientCategory] = Field(None, description="Filter by category")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")

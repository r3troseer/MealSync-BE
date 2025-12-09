from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from app.models.ingredient import UnitOfMeasurement, IngredientCategory
from enum import Enum


class ExportFormat(str, Enum):
    """Export format options for grocery lists."""
    TEXT = "text"
    JSON = "json"


class GroceryListItemCreate(BaseModel):
    """Schema for creating a grocery list item."""
    ingredient_id: Optional[int] = Field(None, description="Ingredient ID (optional for manual items)")
    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    quantity: float = Field(..., gt=0, description="Quantity needed")
    unit: UnitOfMeasurement = Field(..., description="Unit of measurement")
    category: Optional[IngredientCategory] = Field(None, description="Item category for organization")
    notes: Optional[str] = Field(None, max_length=200, description="Additional notes")
    estimated_price: Optional[float] = Field(None, ge=0, description="Estimated price")


class GroceryListItemUpdate(BaseModel):
    """Schema for updating a grocery list item."""
    quantity: Optional[float] = Field(None, gt=0, description="Updated quantity")
    is_purchased: Optional[bool] = Field(None, description="Purchase status")
    notes: Optional[str] = Field(None, max_length=200)
    estimated_price: Optional[float] = Field(None, ge=0)


class GroceryListItemResponse(BaseModel):
    """Schema for grocery list item response."""
    id: int
    uuid: str
    grocery_list_id: int
    ingredient_id: Optional[int]
    name: str
    quantity: float
    unit: UnitOfMeasurement
    category: Optional[IngredientCategory]
    is_purchased: bool
    notes: Optional[str]
    estimated_price: Optional[float]
    purchased_by_id: Optional[int]
    purchased_by_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class GroceryListBase(BaseModel):
    """Base grocery list schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Grocery list name")
    start_date: Optional[date] = Field(None, description="Start date for meal plan")
    end_date: Optional[date] = Field(None, description="End date for meal plan")


class GroceryListCreate(GroceryListBase):
    """Schema for creating a new grocery list."""
    household_id: int = Field(..., description="Household ID")


class GroceryListUpdate(BaseModel):
    """Schema for updating grocery list details."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_completed: Optional[bool] = None


class GroceryListResponse(GroceryListBase):
    """Schema for grocery list response with full details."""
    id: int
    uuid: str
    household_id: int
    created_by_id: int
    is_completed: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # Computed fields
    total_items: int = 0
    purchased_items_count: int = 0
    completion_percentage: float = 0.0

    # Optional expanded data
    items: Optional[List[GroceryListItemResponse]] = None
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class GroceryListGenerate(BaseModel):
    """Schema for generating a grocery list from meals."""
    household_id: int = Field(..., description="Household ID")
    meal_ids: List[int] = Field(..., min_length=1, description="List of meal IDs to generate from")
    name: str = Field(..., min_length=1, max_length=200, description="Name for the grocery list")
    start_date: Optional[date] = Field(None, description="Start date (auto-detected if not provided)")
    end_date: Optional[date] = Field(None, description="End date (auto-detected if not provided)")


class GroceryListExportParams(BaseModel):
    """Schema for grocery list export parameters."""
    format: ExportFormat = Field(ExportFormat.TEXT, description="Export format")
    include_purchased: bool = Field(True, description="Include purchased items in export")
    group_by_category: bool = Field(True, description="Group items by category")


class GroceryListExportResponse(BaseModel):
    """Schema for grocery list export response."""
    format: ExportFormat
    content: str = Field(..., description="Exported content (text or JSON string)")
    filename: str = Field(..., description="Suggested filename for download")

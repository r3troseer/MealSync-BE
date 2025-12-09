from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.grocery_list import (
    GroceryListCreate,
    GroceryListUpdate,
    GroceryListResponse,
    GroceryListGenerate,
    GroceryListItemCreate,
    GroceryListItemUpdate,
    GroceryListItemResponse,
    GroceryListExportParams,
    GroceryListExportResponse
)
from app.schemas.result import Result
from app.services.grocery_list_service import GroceryListService

router = APIRouter()


@router.post("/generate", response_model=Result[GroceryListResponse], status_code=status.HTTP_201_CREATED)
async def generate_from_meals(
    generation_data: GroceryListGenerate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a grocery list from meal IDs."""
    service = GroceryListService(db)
    grocery_list = service.generate_from_meals(current_user.id, generation_data)
    return Result.successful(data=grocery_list)


@router.post("", response_model=Result[GroceryListResponse], status_code=status.HTTP_201_CREATED)
async def create_list(
    list_data: GroceryListCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create an empty grocery list."""
    service = GroceryListService(db)
    grocery_list = service.create_manual_list(current_user.id, list_data)
    return Result.successful(data=grocery_list)


@router.get("", response_model=Result[List[GroceryListResponse]])
async def get_my_lists(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all grocery lists for current user (across all households)."""
    # This would need to be implemented in the service
    # For now, return empty list or implement household-specific version
    return Result.successful(data=[])


@router.get("/households/{household_id}/grocery-lists", response_model=Result[List[GroceryListResponse]])
async def get_household_lists(
    household_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all grocery lists for a household."""
    service = GroceryListService(db)
    lists = service.get_household_lists(household_id, current_user.id, skip, limit)
    return Result.successful(data=lists)


@router.get("/{list_id}", response_model=Result[GroceryListResponse])
async def get_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get grocery list with all items."""
    service = GroceryListService(db)
    grocery_list = service.get_list(list_id, current_user.id)
    return Result.successful(data=grocery_list)


@router.put("/{list_id}", response_model=Result[GroceryListResponse])
async def update_list(
    list_id: int,
    list_data: GroceryListUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update grocery list name or dates."""
    service = GroceryListService(db)
    grocery_list = service.update_list(list_id, current_user.id, list_data)
    return Result.successful(data=grocery_list)


@router.delete("/{list_id}", response_model=Result[dict])
async def delete_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a grocery list."""
    service = GroceryListService(db)
    result = service.delete_list(list_id, current_user.id)
    return Result.successful(data=result)


@router.post("/{list_id}/items", response_model=Result[GroceryListItemResponse], status_code=status.HTTP_201_CREATED)
async def add_item(
    list_id: int,
    item_data: GroceryListItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an item to a grocery list."""
    service = GroceryListService(db)
    item = service.add_item(list_id, current_user.id, item_data)
    return Result.successful(data=item)


@router.patch("/items/{item_id}", response_model=Result[GroceryListItemResponse])
async def update_item(
    item_id: int,
    item_data: GroceryListItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a grocery list item."""
    service = GroceryListService(db)
    item = service.update_item(item_id, current_user.id, item_data)
    return Result.successful(data=item)


@router.patch("/items/{item_id}/purchase", response_model=Result[GroceryListItemResponse])
async def mark_purchased(
    item_id: int,
    is_purchased: bool = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark an item as purchased or unpurchased."""
    service = GroceryListService(db)
    item = service.mark_purchased(item_id, current_user.id, is_purchased)
    return Result.successful(data=item)


@router.delete("/items/{item_id}", response_model=Result[dict])
async def remove_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove an item from a grocery list."""
    service = GroceryListService(db)
    result = service.remove_item(item_id, current_user.id)
    return Result.successful(data=result)


@router.delete("/{list_id}/purchased", response_model=Result[dict])
async def clear_purchased(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all purchased items from a list."""
    service = GroceryListService(db)
    result = service.clear_purchased_items(list_id, current_user.id)
    return Result.successful(data=result)


@router.post("/{list_id}/export", response_model=Result[GroceryListExportResponse])
async def export_list(
    list_id: int,
    export_params: GroceryListExportParams,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export grocery list as text or JSON."""
    service = GroceryListService(db)
    result = service.export_list(list_id, current_user.id, export_params)
    return Result.successful(data=result)

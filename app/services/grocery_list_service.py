from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime
from app.models.grocery_list import GroceryList, GroceryListItem
from app.repositories.grocery_list_repository import GroceryListRepository
from app.repositories.household_repository import HouseholdRepository
from app.repositories.meal_repository import MealRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.schemas.grocery_list import (
    GroceryListCreate,
    GroceryListUpdate,
    GroceryListItemCreate,
    GroceryListItemUpdate,
    GroceryListGenerate,
    GroceryListExportParams,
    ExportFormat
)
from app.core.exception import (
    ResourceNotFoundException,
    BadRequestException,
    AuthorizationException
)


class GroceryListService:
    """Service layer for grocery list operations."""

    def __init__(self, db: Session):
        self.db = db
        self.grocery_list_repo = GroceryListRepository(db)
        self.household_repo = HouseholdRepository(db)
        self.meal_repo = MealRepository(db)
        self.ingredient_repo = IngredientRepository(db)

    def generate_from_meals(self, user_id: int, data: GroceryListGenerate) -> GroceryList:
        """
        Generate a grocery list from meals.

        Args:
            user_id: User creating the list
            data: Generation parameters

        Returns:
            Created grocery list with items

        Raises:
            AuthorizationException: If user not member
            BadRequestException: If meals invalid
        """
        # Verify user is member
        if not self.household_repo.is_member(data.household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Verify all meals belong to household
        meals = [self.meal_repo.get(meal_id) for meal_id in data.meal_ids]

        if any(meal is None for meal in meals):
            raise BadRequestException("One or more meals not found")

        if any(meal.household_id != data.household_id for meal in meals):
            raise BadRequestException("All meals must belong to the specified household")

        # Generate grocery list
        grocery_list = self.grocery_list_repo.generate_from_meals(
            household_id=data.household_id,
            meal_ids=data.meal_ids,
            created_by_id=user_id,
            list_name=data.name
        )

        return grocery_list

    def create_manual_list(self, user_id: int, data: GroceryListCreate) -> GroceryList:
        """Create an empty grocery list."""
        # Verify user is member
        if not self.household_repo.is_member(data.household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Create list
        grocery_list = GroceryList(
            **data.model_dump(),
            created_by_id=user_id,
            is_completed=False
        )

        return self.grocery_list_repo.create(grocery_list)

    def get_list(self, list_id: int, user_id: int) -> GroceryList:
        """Get grocery list with items."""
        grocery_list = self.grocery_list_repo.get_with_items(list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have access to this grocery list")

        return grocery_list

    def get_household_lists(self, household_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[GroceryList]:
        """Get all grocery lists for a household."""
        # Verify user is member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        return self.grocery_list_repo.get_by_household(household_id, skip, limit)

    def update_list(self, list_id: int, user_id: int, data: GroceryListUpdate) -> GroceryList:
        """Update grocery list details."""
        grocery_list = self.grocery_list_repo.get(list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have permission to update this list")

        # Update list
        update_data = data.model_dump(exclude_unset=True)
        updated_list = self.grocery_list_repo.update(list_id, update_data)

        if not updated_list:
            raise ResourceNotFoundException("Grocery list", list_id)

        return updated_list

    def delete_list(self, list_id: int, user_id: int) -> dict:
        """Delete a grocery list."""
        grocery_list = self.grocery_list_repo.get(list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have permission to delete this list")

        # Delete list (items will be cascade deleted)
        self.grocery_list_repo.delete(list_id)

        return {"message": "Grocery list deleted successfully"}

    def add_item(self, list_id: int, user_id: int, item_data: GroceryListItemCreate) -> GroceryListItem:
        """Add an item to a grocery list."""
        grocery_list = self.grocery_list_repo.get(list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have permission to add items to this list")

        # Verify ingredient belongs to household (if provided)
        if item_data.ingredient_id:
            ingredient = self.ingredient_repo.get(item_data.ingredient_id)
            if not ingredient or ingredient.household_id != grocery_list.household_id:
                raise BadRequestException("Ingredient not found or doesn't belong to this household")

        # Add item
        item = self.grocery_list_repo.add_item(list_id, item_data.model_dump())
        return item

    def update_item(self, item_id: int, user_id: int, updates: GroceryListItemUpdate) -> GroceryListItem:
        """Update a grocery list item."""
        item = self.grocery_list_repo.get_item(item_id)
        if not item:
            raise ResourceNotFoundException("Grocery list item", item_id)

        # Get grocery list to verify membership
        grocery_list = self.grocery_list_repo.get(item.grocery_list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", item.grocery_list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have permission to update this item")

        # Update item
        update_data = updates.model_dump(exclude_unset=True)
        updated_item = self.grocery_list_repo.update_item(item_id, update_data)

        if not updated_item:
            raise ResourceNotFoundException("Grocery list item", item_id)

        return updated_item

    def mark_purchased(self, item_id: int, user_id: int, is_purchased: bool) -> GroceryListItem:
        """Mark an item as purchased or unpurchased."""
        item = self.grocery_list_repo.get_item(item_id)
        if not item:
            raise ResourceNotFoundException("Grocery list item", item_id)

        # Get grocery list to verify membership
        grocery_list = self.grocery_list_repo.get(item.grocery_list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", item.grocery_list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have permission to update this item")

        # Mark purchased
        updated_item = self.grocery_list_repo.mark_purchased(item_id, is_purchased, user_id if is_purchased else None)

        if not updated_item:
            raise ResourceNotFoundException("Grocery list item", item_id)

        return updated_item

    def remove_item(self, item_id: int, user_id: int) -> dict:
        """Remove an item from a grocery list."""
        item = self.grocery_list_repo.get_item(item_id)
        if not item:
            raise ResourceNotFoundException("Grocery list item", item_id)

        # Get grocery list to verify membership
        grocery_list = self.grocery_list_repo.get(item.grocery_list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", item.grocery_list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have permission to remove this item")

        # Remove item
        success = self.grocery_list_repo.remove_item(item_id)
        if not success:
            raise ResourceNotFoundException("Grocery list item", item_id)

        return {"message": "Item removed successfully"}

    def clear_purchased_items(self, list_id: int, user_id: int) -> dict:
        """Clear all purchased items from a list."""
        grocery_list = self.grocery_list_repo.get(list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have permission to clear items from this list")

        # Clear purchased items
        count = self.grocery_list_repo.clear_purchased_items(list_id)

        return {
            "message": f"Cleared {count} purchased items",
            "items_cleared": count
        }

    def export_list(self, list_id: int, user_id: int, params: GroceryListExportParams) -> dict:
        """
        Export grocery list in specified format.

        Args:
            list_id: Grocery list ID
            user_id: Requesting user
            params: Export parameters

        Returns:
            Dict with format, content, and filename
        """
        grocery_list = self.grocery_list_repo.get_with_items(list_id)
        if not grocery_list:
            raise ResourceNotFoundException("Grocery list", list_id)

        # Verify user is member
        if not self.household_repo.is_member(grocery_list.household_id, user_id):
            raise AuthorizationException("You don't have access to this grocery list")

        # Filter items if needed
        items = grocery_list.items
        if not params.include_purchased:
            items = [item for item in items if not item.is_purchased]

        # Group by category if requested
        if params.group_by_category:
            items_by_category = {}
            for item in items:
                category = item.category.value if item.category else "Other"
                if category not in items_by_category:
                    items_by_category[category] = []
                items_by_category[category].append(item)
        else:
            items_by_category = {"All Items": items}

        # Generate content based on format
        if params.format == ExportFormat.TEXT:
            content = self._export_as_text(grocery_list, items_by_category)
            filename = f"grocery_list_{grocery_list.id}_{datetime.now().strftime('%Y%m%d')}.txt"
        else:  # JSON
            content = self._export_as_json(grocery_list, items)
            filename = f"grocery_list_{grocery_list.id}_{datetime.now().strftime('%Y%m%d')}.json"

        return {
            "format": params.format.value,
            "content": content,
            "filename": filename
        }

    def _export_as_text(self, grocery_list: GroceryList, items_by_category: dict) -> str:
        """Format grocery list as text."""
        lines = []
        lines.append(f"Grocery List: {grocery_list.name}")
        lines.append(f"Created: {grocery_list.created_at.strftime('%Y-%m-%d')}")
        if grocery_list.start_date and grocery_list.end_date:
            lines.append(f"Period: {grocery_list.start_date} to {grocery_list.end_date}")
        lines.append("")

        for category, items in sorted(items_by_category.items()):
            lines.append(f"=== {category} ===")
            for item in items:
                checkbox = "☑" if item.is_purchased else "☐"
                lines.append(f"{checkbox} {item.quantity} {item.unit.value} {item.name}")
                if item.notes:
                    lines.append(f"   Note: {item.notes}")
            lines.append("")

        return "\n".join(lines)

    def _export_as_json(self, grocery_list: GroceryList, items: List[GroceryListItem]) -> str:
        """Format grocery list as JSON."""
        data = {
            "name": grocery_list.name,
            "created_at": grocery_list.created_at.isoformat(),
            "start_date": grocery_list.start_date.isoformat() if grocery_list.start_date else None,
            "end_date": grocery_list.end_date.isoformat() if grocery_list.end_date else None,
            "is_completed": grocery_list.is_completed,
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit.value,
                    "category": item.category.value if item.category else None,
                    "is_purchased": item.is_purchased,
                    "notes": item.notes,
                    "estimated_price": item.estimated_price
                }
                for item in items
            ]
        }
        return json.dumps(data, indent=2)

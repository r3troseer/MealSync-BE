from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from typing import List, Optional, Dict
from collections import defaultdict
from app.models.grocery_list import GroceryList, GroceryListItem
from app.models.meal import Meal
from app.models.recipe import Recipe
from app.models.ingredient import RecipeIngredient, Ingredient, UnitOfMeasurement
from app.repositories.repository import BaseRepository


class GroceryListRepository(BaseRepository[GroceryList]):
    """Repository for grocery list operations."""

    def __init__(self, db: Session):
        super().__init__(GroceryList, db)

    def get_by_household(self, household_id: int, skip: int = 0, limit: int = 100) -> List[GroceryList]:
        """Get all grocery lists for a household."""
        return (
            self.db.query(GroceryList)
            .filter(GroceryList.household_id == household_id)
            .order_by(GroceryList.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_with_items(self, list_id: int) -> Optional[GroceryList]:
        """Get grocery list with all items eagerly loaded."""
        return (
            self.db.query(GroceryList)
            .options(joinedload(GroceryList.items))
            .filter(GroceryList.id == list_id)
            .first()
        )

    def add_item(self, list_id: int, item_data: dict) -> GroceryListItem:
        """Add an item to a grocery list."""
        item = GroceryListItem(grocery_list_id=list_id, **item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(self, item_id: int) -> bool:
        """Remove an item from a grocery list."""
        item = self.db.query(GroceryListItem).filter(GroceryListItem.id == item_id).first()
        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        return True

    def update_item(self, item_id: int, updates: dict) -> Optional[GroceryListItem]:
        """Update a grocery list item."""
        item = self.db.query(GroceryListItem).filter(GroceryListItem.id == item_id).first()
        if not item:
            return None

        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_purchased(self, item_id: int, is_purchased: bool, user_id: Optional[int] = None) -> Optional[GroceryListItem]:
        """Mark an item as purchased or unpurchased."""
        item = self.db.query(GroceryListItem).filter(GroceryListItem.id == item_id).first()
        if not item:
            return None

        item.is_purchased = is_purchased
        if is_purchased and user_id:
            item.purchased_by_id = user_id
        elif not is_purchased:
            item.purchased_by_id = None

        self.db.commit()
        self.db.refresh(item)
        return item

    def clear_purchased_items(self, list_id: int) -> int:
        """
        Remove all purchased items from a list.

        Returns:
            Number of items deleted
        """
        items = (
            self.db.query(GroceryListItem)
            .filter(
                and_(
                    GroceryListItem.grocery_list_id == list_id,
                    GroceryListItem.is_purchased == True
                )
            )
            .all()
        )

        count = len(items)
        for item in items:
            self.db.delete(item)

        self.db.commit()
        return count

    def generate_from_meals(
        self,
        household_id: int,
        meal_ids: List[int],
        created_by_id: int,
        list_name: str
    ) -> GroceryList:
        """
        Generate a grocery list from multiple meals.

        Aggregates ingredients from all meal recipes and creates a consolidated list.

        Args:
            household_id: Household ID
            meal_ids: List of meal IDs to generate from
            created_by_id: User creating the list
            list_name: Name for the grocery list

        Returns:
            Created grocery list with items
        """
        # Fetch all meals with recipes and ingredients
        meals = (
            self.db.query(Meal)
            .options(
                joinedload(Meal.recipe)
                .joinedload(Recipe.ingredients)
                .joinedload(RecipeIngredient.ingredient)
            )
            .filter(
                and_(
                    Meal.id.in_(meal_ids),
                    Meal.household_id == household_id
                )
            )
            .all()
        )

        # Get date range from meals
        meal_dates = [m.meal_date for m in meals if m.meal_date]
        start_date = min(meal_dates) if meal_dates else None
        end_date = max(meal_dates) if meal_dates else None

        # Create grocery list
        grocery_list = GroceryList(
            name=list_name,
            household_id=household_id,
            created_by_id=created_by_id,
            start_date=start_date,
            end_date=end_date,
            is_completed=False
        )
        self.db.add(grocery_list)
        self.db.flush()  # Get the ID without committing

        # Aggregate ingredients by ingredient_id and unit
        # Key: (ingredient_id, unit) -> Value: total quantity
        ingredient_map: Dict[tuple, dict] = {}

        for meal in meals:
            if not meal.recipe or not meal.recipe.ingredients:
                continue

            # Scale quantities by servings if needed
            servings_multiplier = meal.servings / meal.recipe.servings if meal.recipe.servings else 1

            for recipe_ingredient in meal.recipe.ingredients:
                if recipe_ingredient.is_optional:
                    continue  # Skip optional ingredients

                key = (recipe_ingredient.ingredient_id, recipe_ingredient.unit)

                if key in ingredient_map:
                    # Aggregate quantity
                    ingredient_map[key]['quantity'] += recipe_ingredient.quantity * servings_multiplier
                else:
                    # First occurrence
                    ingredient_map[key] = {
                        'ingredient_id': recipe_ingredient.ingredient_id,
                        'ingredient': recipe_ingredient.ingredient,
                        'quantity': recipe_ingredient.quantity * servings_multiplier,
                        'unit': recipe_ingredient.unit,
                        'notes': recipe_ingredient.notes
                    }

        # Create grocery list items
        for data in ingredient_map.values():
            item = GroceryListItem(
                grocery_list_id=grocery_list.id,
                ingredient_id=data['ingredient_id'],
                name=data['ingredient'].name,
                quantity=round(data['quantity'], 2),  # Round to 2 decimal places
                unit=data['unit'],
                category=data['ingredient'].category,
                notes=data.get('notes'),
                estimated_price=data['ingredient'].average_price,
                is_purchased=False
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(grocery_list)
        return grocery_list

    def get_item(self, item_id: int) -> Optional[GroceryListItem]:
        """Get a grocery list item by ID."""
        return self.db.query(GroceryListItem).filter(GroceryListItem.id == item_id).first()

    def get_active_lists(self, household_id: int) -> List[GroceryList]:
        """Get all active (not completed) grocery lists for a household."""
        return (
            self.db.query(GroceryList)
            .filter(
                and_(
                    GroceryList.household_id == household_id,
                    GroceryList.is_completed == False
                )
            )
            .order_by(GroceryList.created_at.desc())
            .all()
        )

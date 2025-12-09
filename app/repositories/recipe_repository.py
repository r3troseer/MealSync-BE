from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional
from app.models.recipe import Recipe, DifficultyLevel, CuisineType
from app.models.ingredient import RecipeIngredient, Ingredient
from app.repositories.repository import BaseRepository


class RecipeRepository(BaseRepository[Recipe]):
    """Repository for recipe operations."""

    def __init__(self, db: Session):
        super().__init__(Recipe, db)

    def get_by_household(self, household_id: int, skip: int = 0, limit: int = 100) -> List[Recipe]:
        """Get all recipes for a household."""
        return (
            self.db.query(Recipe)
            .filter(Recipe.household_id == household_id)
            .order_by(Recipe.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_with_ingredients(self, recipe_id: int) -> Optional[Recipe]:
        """Get recipe with all ingredients eagerly loaded."""
        return (
            self.db.query(Recipe)
            .options(joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient))
            .filter(Recipe.id == recipe_id)
            .first()
        )

    def search_recipes(
        self,
        household_id: int,
        query: Optional[str] = None,
        cuisine_type: Optional[CuisineType] = None,
        difficulty: Optional[DifficultyLevel] = None,
        min_prep_time: Optional[int] = None,
        max_prep_time: Optional[int] = None,
        min_cook_time: Optional[int] = None,
        max_cook_time: Optional[int] = None,
        ingredient_ids: Optional[List[int]] = None,
        tags: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Recipe]:
        """
        Advanced recipe search with multiple filters.

        Args:
            household_id: Household to search in
            query: Search string for recipe name
            cuisine_type: Filter by cuisine type
            difficulty: Filter by difficulty level
            min_prep_time: Minimum prep time in minutes
            max_prep_time: Maximum prep time in minutes
            min_cook_time: Minimum cook time in minutes
            max_cook_time: Maximum cook time in minutes
            ingredient_ids: Filter recipes containing all these ingredients
            tags: Search in tags (comma-separated)
            skip: Number of records to skip
            limit: Maximum records to return
        """
        filters = [Recipe.household_id == household_id]

        if query:
            filters.append(
                or_(
                    Recipe.name.ilike(f"%{query}%"),
                    Recipe.description.ilike(f"%{query}%")
                )
            )

        if cuisine_type:
            filters.append(Recipe.cuisine_type == cuisine_type)

        if difficulty:
            filters.append(Recipe.difficulty == difficulty)

        if min_prep_time is not None:
            filters.append(Recipe.prep_time_minutes >= min_prep_time)

        if max_prep_time is not None:
            filters.append(Recipe.prep_time_minutes <= max_prep_time)

        if min_cook_time is not None:
            filters.append(Recipe.cook_time_minutes >= min_cook_time)

        if max_cook_time is not None:
            filters.append(Recipe.cook_time_minutes <= max_cook_time)

        if tags:
            # Search for tags (simple contains search)
            filters.append(Recipe.tags.ilike(f"%{tags}%"))

        query_obj = self.db.query(Recipe).filter(and_(*filters))

        # Filter by ingredients if specified (recipe must contain ALL specified ingredients)
        if ingredient_ids:
            for ingredient_id in ingredient_ids:
                query_obj = query_obj.filter(
                    Recipe.ingredients.any(RecipeIngredient.ingredient_id == ingredient_id)
                )

        return query_obj.order_by(Recipe.created_at.desc()).offset(skip).limit(limit).all()

    def add_ingredient(self, recipe_id: int, ingredient_data: dict) -> RecipeIngredient:
        """Add an ingredient to a recipe."""
        recipe_ingredient = RecipeIngredient(recipe_id=recipe_id, **ingredient_data)
        self.db.add(recipe_ingredient)
        self.db.commit()
        self.db.refresh(recipe_ingredient)
        return recipe_ingredient

    def remove_ingredient(self, recipe_id: int, ingredient_id: int) -> bool:
        """Remove an ingredient from a recipe."""
        recipe_ingredient = (
            self.db.query(RecipeIngredient)
            .filter(
                and_(
                    RecipeIngredient.recipe_id == recipe_id,
                    RecipeIngredient.ingredient_id == ingredient_id
                )
            )
            .first()
        )

        if not recipe_ingredient:
            return False

        self.db.delete(recipe_ingredient)
        self.db.commit()
        return True

    def update_ingredients(self, recipe_id: int, ingredients: List[dict]) -> bool:
        """
        Replace all ingredients for a recipe.

        Args:
            recipe_id: Recipe ID
            ingredients: List of ingredient dicts with required fields
        """
        # Delete existing ingredients
        self.db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()

        # Add new ingredients
        for ingredient_data in ingredients:
            recipe_ingredient = RecipeIngredient(recipe_id=recipe_id, **ingredient_data)
            self.db.add(recipe_ingredient)

        self.db.commit()
        return True

    def get_by_creator(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Recipe]:
        """Get all recipes created by a user."""
        return (
            self.db.query(Recipe)
            .filter(Recipe.created_by_id == user_id)
            .order_by(Recipe.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_public_recipes(self, skip: int = 0, limit: int = 100) -> List[Recipe]:
        """Get all public recipes."""
        return (
            self.db.query(Recipe)
            .filter(Recipe.is_public == True)
            .order_by(Recipe.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

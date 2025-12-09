from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.recipe import Recipe
from app.repositories.recipe_repository import RecipeRepository
from app.repositories.household_repository import HouseholdRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.repositories.meal_repository import MealRepository
from app.schemas.recipe import RecipeCreate, RecipeUpdate, RecipeSearchParams
from app.core.exception import (
    ResourceNotFoundException,
    BadRequestException,
    AuthorizationException
)


class RecipeService:
    """Service layer for recipe operations."""

    def __init__(self, db: Session):
        self.db = db
        self.recipe_repo = RecipeRepository(db)
        self.household_repo = HouseholdRepository(db)
        self.ingredient_repo = IngredientRepository(db)
        self.meal_repo = MealRepository(db)

    def create_recipe(self, user_id: int, data: RecipeCreate) -> Recipe:
        """
        Create a new recipe with ingredients.

        Args:
            user_id: User creating the recipe
            data: Recipe creation data

        Returns:
            Created recipe

        Raises:
            AuthorizationException: If user not member of household
            BadRequestException: If ingredients invalid
        """
        # Verify user is member of household
        if not self.household_repo.is_member(data.household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        # Validate all ingredients exist and belong to household
        ingredient_ids = [ing.ingredient_id for ing in data.ingredients]
        ingredients = self.ingredient_repo.get_by_ids(ingredient_ids, data.household_id)

        if len(ingredients) != len(ingredient_ids):
            raise BadRequestException("One or more ingredients are invalid or don't belong to this household")

        # Create recipe (without ingredients first)
        recipe_data = data.model_dump(exclude={'ingredients'})
        recipe = Recipe(**recipe_data, created_by_id=user_id)
        recipe = self.recipe_repo.create(recipe)

        # Add ingredients
        ingredients_data = [ing.model_dump() for ing in data.ingredients]
        self.recipe_repo.update_ingredients(recipe.id, ingredients_data)

        # Refresh to get ingredients
        self.db.refresh(recipe)
        return recipe

    def get_recipe(self, recipe_id: int, user_id: int) -> Recipe:
        """
        Get recipe with ingredients.

        Args:
            recipe_id: Recipe ID
            user_id: Requesting user

        Returns:
            Recipe with ingredients

        Raises:
            AuthorizationException: If user not member of recipe's household
            ResourceNotFoundException: If recipe not found
        """
        recipe = self.recipe_repo.get_with_ingredients(recipe_id)
        if not recipe:
            raise ResourceNotFoundException("Recipe", recipe_id)

        # Verify user is member of household
        if recipe.household_id and not self.household_repo.is_member(recipe.household_id, user_id):
            # Check if recipe is public
            if not recipe.is_public:
                raise AuthorizationException("You don't have access to this recipe")

        return recipe

    def get_household_recipes(self, household_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[Recipe]:
        """Get all recipes for a household."""
        # Verify user is member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        return self.recipe_repo.get_by_household(household_id, skip, limit)

    def update_recipe(self, recipe_id: int, user_id: int, data: RecipeUpdate) -> Recipe:
        """
        Update a recipe.

        Args:
            recipe_id: Recipe ID
            user_id: Requesting user
            data: Update data

        Returns:
            Updated recipe

        Raises:
            AuthorizationException: If user not member
            ResourceNotFoundException: If recipe not found
        """
        recipe = self.recipe_repo.get(recipe_id)
        if not recipe:
            raise ResourceNotFoundException("Recipe", recipe_id)

        # Verify user is member
        if recipe.household_id and not self.household_repo.is_member(recipe.household_id, user_id):
            raise AuthorizationException("You don't have permission to update this recipe")

        # If ingredients are being updated, validate them
        if data.ingredients is not None:
            ingredient_ids = [ing.ingredient_id for ing in data.ingredients]
            ingredients = self.ingredient_repo.get_by_ids(ingredient_ids, recipe.household_id)

            if len(ingredients) != len(ingredient_ids):
                raise BadRequestException("One or more ingredients are invalid")

            # Update ingredients
            ingredients_data = [ing.model_dump() for ing in data.ingredients]
            self.recipe_repo.update_ingredients(recipe_id, ingredients_data)

        # Update recipe fields
        update_data = data.model_dump(exclude={'ingredients'}, exclude_unset=True)
        if update_data:
            updated_recipe = self.recipe_repo.update(recipe_id, update_data)
        else:
            updated_recipe = recipe

        if not updated_recipe:
            raise ResourceNotFoundException("Recipe", recipe_id)

        return updated_recipe

    def delete_recipe(self, recipe_id: int, user_id: int) -> dict:
        """
        Delete a recipe.

        Sets recipe_id to NULL on any meals using this recipe.

        Args:
            recipe_id: Recipe ID
            user_id: Requesting user

        Returns:
            Success message

        Raises:
            AuthorizationException: If user not member
            ResourceNotFoundException: If recipe not found
        """
        recipe = self.recipe_repo.get(recipe_id)
        if not recipe:
            raise ResourceNotFoundException("Recipe", recipe_id)

        # Verify user is member
        if recipe.household_id and not self.household_repo.is_member(recipe.household_id, user_id):
            raise AuthorizationException("You don't have permission to delete this recipe")

        # Get meals using this recipe
        meals = self.meal_repo.get_meals_by_recipe(recipe_id)

        # Set recipe_id to NULL for those meals (orphan them)
        for meal in meals:
            meal.recipe_id = None

        self.db.commit()

        # Delete recipe
        self.recipe_repo.delete(recipe_id)

        return {
            "message": "Recipe deleted successfully",
            "orphaned_meals": len(meals)
        }

    def search_recipes(
        self,
        household_id: int,
        user_id: int,
        params: RecipeSearchParams
    ) -> List[Recipe]:
        """
        Search recipes with filters.

        Args:
            household_id: Household ID
            user_id: Requesting user
            params: Search parameters

        Returns:
            List of matching recipes

        Raises:
            AuthorizationException: If user not member
        """
        # Verify user is member
        if not self.household_repo.is_member(household_id, user_id):
            raise AuthorizationException("You must be a member of the household")

        return self.recipe_repo.search_recipes(
            household_id=household_id,
            query=params.query,
            cuisine_type=params.cuisine_type,
            difficulty=params.difficulty,
            min_prep_time=params.min_prep_time,
            max_prep_time=params.max_prep_time,
            min_cook_time=params.min_cook_time,
            max_cook_time=params.max_cook_time,
            ingredient_ids=params.ingredient_ids,
            tags=params.tags,
            skip=params.skip,
            limit=params.limit
        )

    def get_my_recipes(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Recipe]:
        """Get all recipes created by a user."""
        return self.recipe_repo.get_by_creator(user_id, skip, limit)

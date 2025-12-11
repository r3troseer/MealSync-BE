from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.result import Result
from app.schemas.ai import (
    GenerateIngredientsRequest,
    GenerateIngredientsResponse,
    GenerateRecipeRequest,
    GenerateRecipeResponse,
    GenerateMealPlanRequest,
    GenerateMealPlanResponse
)
from app.schemas.recipe import RecipeCreate
from app.services.ai_service import AIService
from app.core.exception import CustomException, InternalServerException

router = APIRouter()


@router.post("/generate-ingredients", response_model=Result[GenerateIngredientsResponse], status_code=status.HTTP_200_OK)
async def generate_ingredients(
    request: GenerateIngredientsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate ingredient list from meal name using AI.

    - **meal_name**: Name of the meal to generate ingredients for
    - **servings**: Number of servings (default: 4)
    - **dietary_restrictions**: Optional dietary constraints (e.g., vegetarian, gluten-free)
    - **household_id**: Target household for ingredient matching

    Returns list of ingredients with matching to existing household ingredients.
    New ingredients are flagged for user approval before creation.
    """
    try:
        ai_service = AIService(db)

        result = ai_service.generate_ingredients_from_meal(
            meal_name=request.meal_name,
            household_id=request.household_id,
            user_id=current_user.id,
            servings=request.servings,
            dietary_restrictions=request.dietary_restrictions
        )

        return Result.successful(data=result)

    except CustomException:
        raise
    except Exception as e:
        raise InternalServerException(
            message=f"Failed to generate ingredients: {str(e)}"
        )


@router.post("/generate-recipe", response_model=Result[GenerateRecipeResponse], status_code=status.HTTP_200_OK)
async def generate_recipe(
    request: GenerateRecipeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate complete recipe from meal name and optional ingredients.

    - **meal_name**: Name of the meal
    - **ingredient_ids**: Optional list of household ingredient IDs to use (if empty, AI suggests all ingredients)
    - **household_id**: Target household
    - **servings**: Number of servings
    - **difficulty**: Optional difficulty filter
    - **max_prep_time_minutes**: Maximum prep time constraint
    - **cuisine_type**: Optional cuisine type
    - **dietary_restrictions**: Optional dietary constraints

    Returns a complete recipe structure ready for user review and saving.
    Recipe is NOT automatically saved to database.

    If ingredient_ids is empty or not provided, AI will suggest ALL ingredients needed for the recipe.
    """
    try:
        ai_service = AIService(db)

        result = ai_service.generate_recipe_from_meal(
            meal_name=request.meal_name,
            ingredient_ids=request.ingredient_ids,
            household_id=request.household_id,
            user_id=current_user.id,
            servings=request.servings,
            difficulty=request.difficulty.value if request.difficulty else None,
            max_prep_time_minutes=request.max_prep_time_minutes,
            cuisine_type=request.cuisine_type.value if request.cuisine_type else None,
            dietary_restrictions=request.dietary_restrictions
        )

        return Result.successful(data=result)

    except CustomException:
        raise
    except Exception as e:
        raise InternalServerException(
            message=f"Failed to generate recipe: {str(e)}"
        )


@router.post("/generate-meal-plan", response_model=Result[GenerateMealPlanResponse], status_code=status.HTTP_200_OK)
async def generate_meal_plan(
    request: GenerateMealPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate meal plan suggestions from available household ingredients.

    - **household_id**: Target household
    - **days**: Number of days to plan (1-30)
    - **meals_per_day**: Meals per day (1-6)
    - **start_date**: Optional start date (defaults to today)
    - **use_available_only**: Restrict to only available ingredients
    - **dietary_preferences**: Optional dietary constraints
    - **preferred_meal_types**: Optional preferred meal types (breakfast, lunch, dinner, snack)

    Returns meal suggestions grouped by day and meal type.
    Meals are NOT automatically scheduled - user selects which to add.
    """
    try:
        ai_service = AIService(db)

        result = ai_service.generate_meal_plan_from_ingredients(
            household_id=request.household_id,
            user_id=current_user.id,
            days=request.days,
            meals_per_day=request.meals_per_day,
            start_date=request.start_date,
            dietary_preferences=request.dietary_preferences,
            use_available_only=request.use_available_only,
            preferred_meal_types=[mt.value for mt in request.preferred_meal_types] if request.preferred_meal_types else None
        )

        return Result.successful(data=result)

    except CustomException:
        raise
    except Exception as e:
        raise InternalServerException(
            message=f"Failed to generate meal plan: {str(e)}"
        )


@router.post("/save-recipe", response_model=Result[dict], status_code=status.HTTP_201_CREATED)
async def save_recipe_with_auto_create(
    recipe_data: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save a recipe with automatic creation of missing ingredients.

    Designed for AI-generated recipes where ingredients may not exist yet.
    For standard recipe creation with existing ingredients, use POST /recipes.

    This endpoint differs from /recipes by:
    - Auto-creating ingredients when ingredient_id is None
    - Requiring ingredient_name for new ingredients
    - Relaxing validation on ingredient existence

    Request Body:
    - Standard RecipeCreate schema
    - For new ingredients: Set ingredient_id=None, provide ingredient_name
    - For existing ingredients: Provide ingredient_id only

    Returns:
    - recipe_id: Created recipe ID
    - recipe_uuid: Recipe UUID for retrieval
    - created_ingredients_count: Number of ingredients auto-created
    """
    try:
        ai_service = AIService(db)

        recipe = ai_service.save_recipe_with_ingredient_creation(
            recipe_data=recipe_data,
            user_id=current_user.id
        )

        # Count how many ingredients were created
        created_count = sum(
            1 for ing in recipe_data.ingredients
            if ing.ingredient_id is None
        )

        return Result.successful(data={
            "message": "Recipe saved successfully",
            "recipe_id": recipe.id,
            "recipe_uuid": recipe.uuid,
            "created_ingredients_count": created_count
        })

    except CustomException:
        raise
    except Exception as e:
        raise InternalServerException(
            message=f"Failed to save recipe: {str(e)}"
        )

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.recipe import RecipeCreate, RecipeUpdate, RecipeResponse, RecipeSearchParams
from app.schemas.result import Result
from app.services.recipe_service import RecipeService

router = APIRouter()


@router.post("", response_model=Result[RecipeResponse], status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe_data: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new recipe with ingredients."""
    service = RecipeService(db)
    recipe = service.create_recipe(current_user.id, recipe_data)
    return Result.successful(data=recipe)


@router.get("", response_model=Result[List[RecipeResponse]])
async def get_my_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all recipes created by current user."""
    service = RecipeService(db)
    recipes = service.get_my_recipes(current_user.id, skip, limit)
    return Result.successful(data=recipes)


@router.get("/{recipe_id}", response_model=Result[RecipeResponse])
async def get_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recipe details with ingredients."""
    service = RecipeService(db)
    recipe = service.get_recipe(recipe_id, current_user.id)
    return Result.successful(data=recipe)


@router.put("/{recipe_id}", response_model=Result[RecipeResponse])
async def update_recipe(
    recipe_id: int,
    recipe_data: RecipeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update recipe details and/or ingredients."""
    service = RecipeService(db)
    recipe = service.update_recipe(recipe_id, current_user.id, recipe_data)
    return Result.successful(data=recipe)


@router.delete("/{recipe_id}", response_model=Result[dict])
async def delete_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a recipe (sets recipe_id to NULL on related meals)."""
    service = RecipeService(db)
    result = service.delete_recipe(recipe_id, current_user.id)
    return Result.successful(data=result)


@router.get("/households/{household_id}/recipes", response_model=Result[List[RecipeResponse]])
async def get_household_recipes(
    household_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all recipes for a household."""
    service = RecipeService(db)
    recipes = service.get_household_recipes(household_id, current_user.id, skip, limit)
    return Result.successful(data=recipes)


@router.post("/search", response_model=Result[List[RecipeResponse]])
async def search_recipes(
    search_params: RecipeSearchParams,
    household_id: int = Query(..., description="Household ID to search in"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search recipes with advanced filters."""
    service = RecipeService(db)
    recipes = service.search_recipes(household_id, current_user.id, search_params)
    return Result.successful(data=recipes)

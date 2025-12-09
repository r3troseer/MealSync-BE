from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.ingredient import IngredientCategory
from app.schemas.ingredient import (
    IngredientCreate,
    IngredientUpdate,
    IngredientResponse
)
from app.schemas.result import Result
from app.repositories.ingredient_repository import IngredientRepository
from app.repositories.household_repository import HouseholdRepository
from app.core.exception import AuthorizationException, ResourceNotFoundException, BadRequestException

router = APIRouter()


@router.post("/households/{household_id}/ingredients", response_model=Result[IngredientResponse], status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    household_id: int,
    ingredient_data: IngredientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new ingredient for a household."""
    household_repo = HouseholdRepository(db)
    ingredient_repo = IngredientRepository(db)

    # Verify user is member
    if not household_repo.is_member(household_id, current_user.id):
        raise AuthorizationException("You must be a member of the household")

    # Check for duplicate name
    if ingredient_repo.exists_by_name(household_id, ingredient_data.name):
        raise BadRequestException(f"Ingredient '{ingredient_data.name}' already exists in this household")

    # Create ingredient
    from app.models.ingredient import Ingredient
    ingredient = Ingredient(**ingredient_data.model_dump())
    ingredient = ingredient_repo.create(ingredient)

    return Result.successful(data=ingredient)


@router.get("/households/{household_id}/ingredients", response_model=Result[List[IngredientResponse]])
async def get_ingredients(
    household_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all ingredients for a household."""
    household_repo = HouseholdRepository(db)
    ingredient_repo = IngredientRepository(db)

    # Verify user is member
    if not household_repo.is_member(household_id, current_user.id):
        raise AuthorizationException("You must be a member of the household")

    ingredients = ingredient_repo.get_by_household(household_id, skip, limit)
    return Result.successful(data=ingredients)


@router.get("/ingredients/{ingredient_id}", response_model=Result[IngredientResponse])
async def get_ingredient(
    ingredient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ingredient details."""
    household_repo = HouseholdRepository(db)
    ingredient_repo = IngredientRepository(db)

    ingredient = ingredient_repo.get(ingredient_id)
    if not ingredient:
        raise ResourceNotFoundException("Ingredient", ingredient_id)

    # Verify user is member
    if not household_repo.is_member(ingredient.household_id, current_user.id):
        raise AuthorizationException("You don't have access to this ingredient")

    return Result.successful(data=ingredient)


@router.put("/ingredients/{ingredient_id}", response_model=Result[IngredientResponse])
async def update_ingredient(
    ingredient_id: int,
    ingredient_data: IngredientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update ingredient details."""
    household_repo = HouseholdRepository(db)
    ingredient_repo = IngredientRepository(db)

    ingredient = ingredient_repo.get(ingredient_id)
    if not ingredient:
        raise ResourceNotFoundException("Ingredient", ingredient_id)

    # Verify user is member
    if not household_repo.is_member(ingredient.household_id, current_user.id):
        raise AuthorizationException("You don't have permission to update this ingredient")

    # Check for duplicate name if name is being updated
    if ingredient_data.name:
        if ingredient_repo.exists_by_name(ingredient.household_id, ingredient_data.name, exclude_id=ingredient_id):
            raise BadRequestException(f"Ingredient '{ingredient_data.name}' already exists in this household")

    # Update ingredient
    update_data = ingredient_data.model_dump(exclude_unset=True)
    updated_ingredient = ingredient_repo.update(ingredient_id, update_data)

    if not updated_ingredient:
        raise ResourceNotFoundException("Ingredient", ingredient_id)

    return Result.successful(data=updated_ingredient)


@router.delete("/ingredients/{ingredient_id}", response_model=Result[dict])
async def delete_ingredient(
    ingredient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an ingredient."""
    household_repo = HouseholdRepository(db)
    ingredient_repo = IngredientRepository(db)

    ingredient = ingredient_repo.get(ingredient_id)
    if not ingredient:
        raise ResourceNotFoundException("Ingredient", ingredient_id)

    # Verify user is member
    if not household_repo.is_member(ingredient.household_id, current_user.id):
        raise AuthorizationException("You don't have permission to delete this ingredient")

    # Delete ingredient
    ingredient_repo.delete(ingredient_id)

    return Result.successful(data={"message": "Ingredient deleted successfully"})


@router.get("/households/{household_id}/ingredients/search", response_model=Result[List[IngredientResponse]])
async def search_ingredients(
    household_id: int,
    query: Optional[str] = Query(None, min_length=1),
    category: Optional[IngredientCategory] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search ingredients with filters."""
    household_repo = HouseholdRepository(db)
    ingredient_repo = IngredientRepository(db)

    # Verify user is member
    if not household_repo.is_member(household_id, current_user.id):
        raise AuthorizationException("You must be a member of the household")

    ingredients = ingredient_repo.search(household_id, query, category, skip, limit)
    return Result.successful(data=ingredients)

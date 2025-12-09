from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from app.models.ingredient import Ingredient, IngredientCategory
from app.repositories.repository import BaseRepository


class IngredientRepository(BaseRepository[Ingredient]):
    """Repository for ingredient operations."""

    def __init__(self, db: Session):
        super().__init__(Ingredient, db)

    def get_by_household(self, household_id: int, skip: int = 0, limit: int = 100) -> List[Ingredient]:
        """Get all ingredients for a household."""
        return (
            self.db.query(Ingredient)
            .filter(Ingredient.household_id == household_id)
            .order_by(Ingredient.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_name(self, household_id: int, name: str) -> Optional[Ingredient]:
        """Find ingredient by exact name within a household."""
        return (
            self.db.query(Ingredient)
            .filter(
                and_(
                    Ingredient.household_id == household_id,
                    func.lower(Ingredient.name) == name.lower()
                )
            )
            .first()
        )

    def search(
        self,
        household_id: int,
        query: Optional[str] = None,
        category: Optional[IngredientCategory] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Ingredient]:
        """
        Search ingredients with filters.

        Args:
            household_id: Household to search in
            query: Search string for ingredient name (case-insensitive)
            category: Filter by category
            skip: Number of records to skip
            limit: Maximum records to return
        """
        filters = [Ingredient.household_id == household_id]

        if query:
            filters.append(Ingredient.name.ilike(f"%{query}%"))

        if category:
            filters.append(Ingredient.category == category)

        return (
            self.db.query(Ingredient)
            .filter(and_(*filters))
            .order_by(Ingredient.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_category(self, household_id: int, category: IngredientCategory) -> List[Ingredient]:
        """Get all ingredients in a specific category for a household."""
        return (
            self.db.query(Ingredient)
            .filter(
                and_(
                    Ingredient.household_id == household_id,
                    Ingredient.category == category
                )
            )
            .order_by(Ingredient.name)
            .all()
        )

    def exists_by_name(self, household_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check if an ingredient with this name exists in the household.

        Args:
            household_id: Household to check in
            name: Ingredient name (case-insensitive)
            exclude_id: Optional ingredient ID to exclude (for updates)
        """
        query = self.db.query(Ingredient).filter(
            and_(
                Ingredient.household_id == household_id,
                func.lower(Ingredient.name) == name.lower()
            )
        )

        if exclude_id:
            query = query.filter(Ingredient.id != exclude_id)

        return query.first() is not None

    def get_by_ids(self, ingredient_ids: List[int], household_id: Optional[int] = None) -> List[Ingredient]:
        """
        Get multiple ingredients by IDs.

        Args:
            ingredient_ids: List of ingredient IDs
            household_id: Optional household filter for security
        """
        query = self.db.query(Ingredient).filter(Ingredient.id.in_(ingredient_ids))

        if household_id:
            query = query.filter(Ingredient.household_id == household_id)

        return query.all()

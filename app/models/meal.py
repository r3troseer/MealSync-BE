from sqlalchemy import String, Date, ForeignKey, Enum as SQLEnum, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from datetime import date
import enum
from app.models.base import BaseModel
if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.recipe import Recipe
    from app.models.user import User


class MealType(str, enum.Enum):
    """Types of meals"""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MealStatus(str, enum.Enum):
    """Meal preparation status"""

    PLANNED = "planned"
    PREPARING = "preparing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Meal(BaseModel):
    """
    Meal model for planned meals in a household.
    Links to recipes and assigns cooking responsibility.
    """

    __tablename__ = "meals"

    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    meal_type: Mapped[MealType] = mapped_column(
        SQLEnum(MealType), nullable=False, index=True
    )
    meal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Status
    status: Mapped[MealStatus] = mapped_column(
        SQLEnum(MealStatus), default=MealStatus.PLANNED, nullable=False
    )

    # Details
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    servings: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Foreign keys
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )

    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    recipe_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    household: Mapped["Household"] = relationship(
        "Household", back_populates="meals", lazy="selectin"
    )

    assigned_to_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_meals",
        foreign_keys=[assigned_to_id],
        lazy="selectin",
    )

    recipe: Mapped[Optional["Recipe"]] = relationship(
        "Recipe", back_populates="meals", lazy="selectin"
    )

    @property
    def is_assigned(self) -> bool:
        """Check if meal has someone assigned to cook it"""
        return self.assigned_to_id is not None

    @property
    def has_recipe(self) -> bool:
        """Check if meal has an associated recipe"""
        return self.recipe_id is not None

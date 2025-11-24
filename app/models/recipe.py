from sqlalchemy import String, Integer, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING
import enum
from app.models.base import BaseModel
if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.ingredient import RecipeIngredient
    from app.models.meal import Meal
    from app.models.user import User


class DifficultyLevel(str, enum.Enum):
    """Recipe difficulty levels"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CuisineType(str, enum.Enum):
    """Common cuisine types"""

    ITALIAN = "italian"
    CHINESE = "chinese"
    MEXICAN = "mexican"
    INDIAN = "indian"
    JAPANESE = "japanese"
    AMERICAN = "american"
    FRENCH = "french"
    THAI = "thai"
    MEDITERRANEAN = "mediterranean"
    MIDDLE_EASTERN = "middle_eastern"
    KOREAN = "korean"
    VIETNAMESE = "vietnamese"
    OTHER = "other"


class Recipe(BaseModel):
    """
    Recipe model for storing meal recipes.
    Can be personal or shared within a household.
    """

    __tablename__ = "recipes"

    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None
    )

    # Cooking details
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    prep_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )
    cook_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )
    servings: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Classification
    difficulty: Mapped[Optional[DifficultyLevel]] = mapped_column(
        SQLEnum(DifficultyLevel), nullable=True, default=None
    )
    cuisine_type: Mapped[Optional[CuisineType]] = mapped_column(
        SQLEnum(CuisineType), nullable=True, default=None
    )

    # Tags and categories (stored as comma-separated string or JSON)
    tags: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )

    # Nutritional info (optional)
    calories_per_serving: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )

    # Recipe source
    source_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )

    # Image
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )

    # Sharing settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Foreign keys
    household_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=True, index=True
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    household: Mapped[Optional["Household"]] = relationship(
        "Household", back_populates="recipes", lazy="selectin"
    )

    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="created_recipes",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )

    ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    meals: Mapped[List["Meal"]] = relationship(
        "Meal", back_populates="recipe", lazy="selectin"
    )

    @property
    def total_time_minutes(self) -> Optional[int]:
        """Calculate total cooking time"""
        if self.prep_time_minutes and self.cook_time_minutes:
            return self.prep_time_minutes + self.cook_time_minutes
        return None

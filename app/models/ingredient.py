from sqlalchemy import String, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
import enum
from app.models.base import BaseModel
if TYPE_CHECKING:
    from app.models.recipe import Recipe
    from app.models.household import Household

class IngredientCategory(str, enum.Enum):
    """Categories for organizing ingredients"""

    PRODUCE = "produce"
    MEAT = "meat"
    SEAFOOD = "seafood"
    DAIRY = "dairy"
    BAKERY = "bakery"
    PANTRY = "pantry"
    SPICES = "spices"
    BEVERAGES = "beverages"
    FROZEN = "frozen"
    SNACKS = "snacks"
    OTHER = "other"


class UnitOfMeasurement(str, enum.Enum):
    """Common units of measurement"""

    # Weight
    GRAM = "gram"
    KILOGRAM = "kilogram"
    OUNCE = "ounce"
    POUND = "pound"

    # Volume
    MILLILITER = "milliliter"
    LITER = "liter"
    TEASPOON = "teaspoon"
    TABLESPOON = "tablespoon"
    CUP = "cup"
    PINT = "pint"
    QUART = "quart"
    GALLON = "gallon"

    # Count
    PIECE = "piece"
    SLICE = "slice"
    CLOVE = "clove"
    PACKAGE = "package"
    CAN = "can"
    BUNCH = "bunch"

    # Other
    TO_TASTE = "to_taste"
    AS_NEEDED = "as_needed"


class Ingredient(BaseModel):
    """
    Household-scoped ingredient list.
    Stores ingredients used across recipes within a household.
    """

    __tablename__ = "ingredients"

    # Basic info
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    category: Mapped[Optional[IngredientCategory]] = mapped_column(
        SQLEnum(IngredientCategory), nullable=True, default=None
    )

    # Household scope
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Optional details
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )

    # Average price (optional, for cost estimation)
    average_price: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )
    price_unit: Mapped[Optional[UnitOfMeasurement]] = mapped_column(
        SQLEnum(UnitOfMeasurement), nullable=True, default=None
    )

    # Relationships
    household: Mapped["Household"] = relationship("Household", lazy="selectin")

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="ingredient", cascade="all, delete-orphan"
    )


class RecipeIngredient(BaseModel):
    """
    Junction table linking recipes to ingredients with quantities.
    Stores the specific amount of each ingredient needed for a recipe.
    """

    __tablename__ = "recipe_ingredients"

    # Foreign keys
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Quantity details
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[UnitOfMeasurement] = mapped_column(
        SQLEnum(UnitOfMeasurement), nullable=False
    )

    # Optional notes (e.g., "chopped", "diced", "optional")
    notes: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )

    # Is this ingredient optional?
    is_optional: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Display order in recipe
    order: Mapped[Optional[int]] = mapped_column(default=0, nullable=True)

    # Relationships
    recipe: Mapped["Recipe"] = relationship(
        "Recipe", back_populates="ingredients", lazy="selectin"
    )

    ingredient: Mapped["Ingredient"] = relationship(
        "Ingredient", back_populates="recipe_ingredients", lazy="selectin"
    )

    @property
    def display_quantity(self) -> str:
        """Format quantity for display"""
        if self.quantity == int(self.quantity):
            return f"{int(self.quantity)} {self.unit.value}"
        return f"{self.quantity} {self.unit.value}"

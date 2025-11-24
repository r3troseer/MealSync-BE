from sqlalchemy import String, ForeignKey, Boolean, Date, Float, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import date
from app.models.base import BaseModel
from app.models.ingredient import Ingredient, UnitOfMeasurement, IngredientCategory
if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.user import User
    from app.models.ingredient import Ingredient, UnitOfMeasurement, IngredientCategory

class GroceryList(BaseModel):
    """
    Grocery list for a household.
    Can be generated from meal plans or created manually.
    """

    __tablename__ = "grocery_lists"

    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, default=None
    )
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=None)

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Foreign keys
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    household: Mapped["Household"] = relationship(
        "Household", back_populates="grocery_lists", lazy="selectin"
    )

    created_by: Mapped["User"] = relationship("User", lazy="selectin")

    items: Mapped[List["GroceryListItem"]] = relationship(
        "GroceryListItem",
        back_populates="grocery_list",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def total_items(self) -> int:
        """Total number of items in list"""
        return len(self.items)

    @property
    def purchased_items_count(self) -> int:
        """Number of purchased items"""
        return sum(1 for item in self.items if item.is_purchased)

    @property
    def completion_percentage(self) -> float:
        """Percentage of items purchased"""
        if self.total_items == 0:
            return 0.0
        return (self.purchased_items_count / self.total_items) * 100


class GroceryListItem(BaseModel):
    """
    Individual item in a grocery list.
    """

    __tablename__ = "grocery_list_items"

    # Item details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped["UnitOfMeasurement"] = mapped_column(
        SQLEnum(UnitOfMeasurement), nullable=False
    )

    # Category for organizing list
    category: Mapped[Optional["IngredientCategory"]] = mapped_column(
        SQLEnum(IngredientCategory), nullable=True, default=None
    )

    # Purchase status
    is_purchased: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Optional details
    notes: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None
    )
    estimated_price: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )

    # Foreign keys
    grocery_list_id: Mapped[int] = mapped_column(
        ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )

    ingredient_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True, index=True
    )

    purchased_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    grocery_list: Mapped["GroceryList"] = relationship(
        "GroceryList", back_populates="items", lazy="selectin"
    )

    ingredient: Mapped[Optional["Ingredient"]] = relationship(
        "Ingredient", lazy="selectin"
    )

    purchased_by: Mapped[Optional["User"]] = relationship("User", lazy="selectin")

    @property
    def display_quantity(self) -> str:
        """Format quantity for display"""
        if self.quantity == int(self.quantity):
            return f"{int(self.quantity)} {self.unit.value}"
        return f"{self.quantity} {self.unit.value}"

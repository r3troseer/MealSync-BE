from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING
from app.models.base import BaseModel
from app.models.associations import user_household

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.meal import Meal
    from app.models.recipe import Recipe
    from app.models.grocery_list import GroceryList


class Household(BaseModel):
    """
    Household model for grouping users (flatmates).
    A household can have multiple members and shared meal plans.
    """

    __tablename__ = "households"

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )

    # Invitation code for joining household
    invite_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Creator/owner
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    members: Mapped[List["User"]] = relationship(
        "User", secondary=user_household, back_populates="households", lazy="selectin"
    )

    created_by: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by_id], lazy="selectin"
    )

    meals: Mapped[List["Meal"]] = relationship(
        "Meal",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    grocery_lists: Mapped[List["GroceryList"]] = relationship(
        "GroceryList",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

from sqlalchemy import String, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List, TYPE_CHECKING
from app.models.base import BaseModel
from app.models.associations import user_household
if TYPE_CHECKING:
    from app.models.household import Household
    from app.models.meal import Meal
    from app.models.recipe import Recipe


# user_household = Table(
#     'user_household',
#     Base.metadata,
#     Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
#     Column('household_id', Integer, ForeignKey('households.id', ondelete='CASCADE'))
# )


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    
    # Preferences
    dietary_preferences: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    allergies: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    # quotes for forward references before models are defined
    households: Mapped[List["Household"]] = relationship(  
        "Household",
        secondary=user_household,
        back_populates="members",
        lazy="selectin"
    )
    assigned_meals: Mapped[List["Meal"]] = relationship( 
        "Meal",
        back_populates="assigned_to_user",
        foreign_keys="[Meal.assigned_to_id]",
        lazy="selectin"
    )
    created_recipes: Mapped[List["Recipe"]] = relationship( 
        "Recipe",
        back_populates="created_by_user",
        foreign_keys="[Recipe.created_by_id]",
        lazy="selectin"
    )
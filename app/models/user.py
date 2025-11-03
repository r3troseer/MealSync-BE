from sqlalchemy import Column, String, Boolean, Integer, Table, ForeignKey
from sqlalchemy.orm import relationship
from models.baseModel import Base

user_household = Table(
    'user_household',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('household_id', Integer, ForeignKey('households.id', ondelete='CASCADE'))
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    # Preferences
    dietary_preferences = Column(String, nullable=True)  # JSON string or separate table
    allergies = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    
    # Relationships
    households = relationship(
        "Household",
        secondary=user_household,
        back_populates="members"
    )
    assigned_meals = relationship("Meal", back_populates="assigned_to_user")
    created_recipes = relationship("Recipe", back_populates="created_by_user")
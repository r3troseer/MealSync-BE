from sqlalchemy.orm import Session
from typing import Generic, Type, TypeVar, List, Optional, Dict, Any
from app.models.base import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[T], db: Session):
        """
        Initialize repository with model and database session.

        Args:
            model: The SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get(self, id: int) -> Optional[T]:
        """Get a single record by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_by_uuid(self, uuid: str) -> Optional[T]:
        """Get a single record by UUID."""
        return self.db.query(self.model).filter(self.model.uuid == uuid).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj: T) -> T:
        """Create a new record."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_from_dict(self, data: Dict[str, Any]) -> T:
        """Create a new record from dictionary."""
        obj = self.model(**data)
        return self.create(obj)

    def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID."""
        obj = self.get(id)
        if not obj:
            return None

        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: int) -> bool:
        """Delete a record by ID. Returns True if deleted, False if not found."""
        obj = self.get(id)
        if not obj:
            return False

        self.db.delete(obj)
        self.db.commit()
        return True

    def exists(self, id: int) -> bool:
        """Check if a record exists by ID."""
        return self.db.query(self.model).filter(self.model.id == id).count() > 0

    def exists_by_uuid(self, uuid: str) -> bool:
        """Check if a record exists by UUID."""
        return self.db.query(self.model).filter(self.model.uuid == uuid).count() > 0

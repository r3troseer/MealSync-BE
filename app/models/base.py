from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from typing import Optional
# from config.database import engine
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    """Base class for all models"""
    pass


# @as_declarative()
class BaseModel(Base):

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        String(36), 
        default=lambda: str(uuid.uuid4()), 
        unique=True, 
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True
    )
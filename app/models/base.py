from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import as_declarative, declared_attr
# from config.database import engine
# from datetime import datetime
import uuid

@as_declarative()
class Base:
    __name__: str
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

# Configure database engine with appropriate settings
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support connection pooling arguments
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG
    )
else:
    # Configure connection pool for PostgreSQL/MySQL
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections after 1 hour
        pool_size=10,        # Increase pool size from default 5
        max_overflow=20,     # Allow more overflow connections
        echo=settings.DEBUG
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Database session dependency for FastAPI.
    Properly manages session lifecycle - creates, yields, and closes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
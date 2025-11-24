from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  
    echo=settings.DEBUG  
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def get_db():
    db = scoped_session(SessionLocal)
    try:
        yield db
    finally:
        db.remove()
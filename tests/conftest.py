import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set required environment variables for testing
os.environ["API_V1_STR"] = "/api/v1"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.database import get_db
from app.models.base import Base

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine for the entire test session."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine):
    """
    Create a new database session for each test.
    Automatically rolls back changes after each test.
    """
    # Start a connection that we can use for the test
    connection = engine.connect()

    # Begin a transaction
    transaction = connection.begin()

    # Create session bound to the connection
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection
    )
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass  # Don't close here, we'll handle it after the test

    app.dependency_overrides[get_db] = override_get_db
    yield session

    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session):
    """Create a FastAPI TestClient with database session override."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(db_session):
    """Create a test user for authentication tests."""
    from app.models.user import User
    from app.utils.security import get_password_hash

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(client, test_user):
    """Get authentication token for test user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"}
    )
    return response.json()["data"]["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers with bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}

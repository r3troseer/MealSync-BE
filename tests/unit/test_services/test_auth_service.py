import pytest
from sqlalchemy.orm import Session
from app.services.authService import AuthService
from app.schemas.user import UserCreate
from app.core.exception import AuthenticationException, AuthorizationException
from app.utils.security import decode_access_token


@pytest.mark.unit
class TestAuthService:
    """Unit tests for AuthService."""

    def test_register_success(self, db_session: Session):
        """Test successful user registration."""
        auth_service = AuthService(db_session)
        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            password="password123",
            full_name="New User"
        )

        user = auth_service.register(user_data)

        assert user is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.is_active is True
        assert user.hashed_password != "password123"  # Should be hashed

    def test_register_duplicate_username(self, db_session: Session, test_user):
        """Test registration with duplicate username fails."""
        auth_service = AuthService(db_session)
        user_data = UserCreate(
            username="testuser",  # Already exists
            email="different@example.com",
            password="password123"
        )

        with pytest.raises(Exception):  # Should raise validation/uniqueness error
            auth_service.register(user_data)

    def test_login_success(self, db_session: Session, test_user):
        """Test successful login with valid credentials."""
        auth_service = AuthService(db_session)

        token = auth_service.login("testuser", "testpass123")

        assert token is not None
        assert token.access_token is not None
        assert token.refresh_token is not None
        assert token.token_type == "bearer"

        # Verify token contains correct user data
        payload = decode_access_token(token.access_token)
        assert payload is not None
        assert int(payload["sub"]) == test_user.id
        assert payload["username"] == test_user.username

    def test_login_with_email(self, db_session: Session, test_user):
        """Test login using email instead of username."""
        auth_service = AuthService(db_session)

        token = auth_service.login("test@example.com", "testpass123")

        assert token is not None
        assert token.access_token is not None

    def test_login_invalid_username(self, db_session: Session):
        """Test login with non-existent username."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.login("nonexistent", "password123")

        assert "Incorrect username or password" in str(exc_info.value)

    def test_login_invalid_password(self, db_session: Session, test_user):
        """Test login with incorrect password."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.login("testuser", "wrongpassword")

        assert "Incorrect username or password" in str(exc_info.value)

    def test_login_inactive_user(self, db_session: Session, test_user):
        """Test login with deactivated user account."""
        auth_service = AuthService(db_session)

        # Deactivate user
        test_user.is_active = False
        db_session.commit()

        with pytest.raises(AuthorizationException) as exc_info:
            auth_service.login("testuser", "testpass123")

        assert "Account is deactivated" in str(exc_info.value)

    def test_refresh_access_token_success(self, db_session: Session, test_user):
        """Test successful token refresh."""
        auth_service = AuthService(db_session)

        # First login to get refresh token
        login_token = auth_service.login("testuser", "testpass123")
        refresh_token = login_token.refresh_token

        # Refresh the access token
        new_token = auth_service.refresh_access_token(refresh_token)

        assert new_token is not None
        assert new_token.access_token is not None
        assert new_token.token_type == "bearer"
        # Note: Tokens might be identical if generated at same timestamp, which is OK

    def test_refresh_with_invalid_token(self, db_session: Session):
        """Test refresh with invalid refresh token."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.refresh_access_token("invalid_token")

        assert "Could not validate" in str(exc_info.value)

    def test_refresh_with_access_token(self, db_session: Session, test_user):
        """Test refresh fails when using access token instead of refresh token."""
        auth_service = AuthService(db_session)

        # Get access token (not refresh token)
        login_token = auth_service.login("testuser", "testpass123")
        access_token = login_token.access_token

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.refresh_access_token(access_token)

        assert "Could not validate refresh token" in str(exc_info.value)

    def test_verify_token_success(self, db_session: Session, test_user):
        """Test successful token verification."""
        auth_service = AuthService(db_session)

        # Get valid token
        login_token = auth_service.login("testuser", "testpass123")

        # Verify token
        user = auth_service.verify_token(login_token.access_token)

        assert user is not None
        assert user.id == test_user.id
        assert user.username == test_user.username

    def test_verify_invalid_token(self, db_session: Session):
        """Test verification with invalid token."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.verify_token("invalid_token")

        assert "Could not validate credentials" in str(exc_info.value)

    def test_verify_token_inactive_user(self, db_session: Session, test_user):
        """Test verification fails for deactivated user."""
        auth_service = AuthService(db_session)

        # Get valid token first
        login_token = auth_service.login("testuser", "testpass123")

        # Deactivate user
        test_user.is_active = False
        db_session.commit()

        with pytest.raises(AuthorizationException) as exc_info:
            auth_service.verify_token(login_token.access_token)

        assert "Account is deactivated" in str(exc_info.value)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.core.auth import get_password_hash
from main import app
from datetime import datetime, timedelta

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_password_reset.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Drop tables after test
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "password": "TestPass123",
        "first_name": "Test",
        "last_name": "User",
        "role": "student"
    }

class TestPasswordResetFlow:
    def test_complete_password_reset_flow(self, client, test_user_data):
        """Test the complete password reset flow."""
        # Register user first
        client.post("/api/auth/register", json=test_user_data)
        
        # Request password reset
        response = client.post("/api/auth/request-password-reset", json={
            "email": test_user_data["email"]
        })
        assert response.status_code == 200
        
        # Get the reset token from database (in real app, this would be sent via email)
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        reset_token = user.reset_token
        assert reset_token is not None
        assert user.reset_token_expires > datetime.utcnow()
        db.close()
        
        # Reset password with token
        new_password = "NewPassword123"
        response = client.post("/api/auth/reset-password", json={
            "token": reset_token,
            "new_password": new_password
        })
        assert response.status_code == 200
        
        # Verify old password no longer works
        response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 401
        
        # Verify new password works
        response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": new_password
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_reset_password_with_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.post("/api/auth/reset-password", json={
            "token": "invalid-token",
            "new_password": "NewPassword123"
        })
        assert response.status_code == 400
        assert "Invalid or expired reset token" in response.json()["detail"]
    
    def test_reset_password_with_expired_token(self, client, test_user_data):
        """Test password reset with expired token."""
        # Register user first
        client.post("/api/auth/register", json=test_user_data)
        
        # Request password reset
        client.post("/api/auth/request-password-reset", json={
            "email": test_user_data["email"]
        })
        
        # Manually expire the token
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        reset_token = user.reset_token
        user.reset_token_expires = datetime.utcnow() - timedelta(hours=1)  # Expired
        db.commit()
        db.close()
        
        # Try to reset password with expired token
        response = client.post("/api/auth/reset-password", json={
            "token": reset_token,
            "new_password": "NewPassword123"
        })
        assert response.status_code == 400
        assert "Invalid or expired reset token" in response.json()["detail"]
    
    def test_reset_password_clears_token(self, client, test_user_data):
        """Test that password reset clears the reset token."""
        # Register user first
        client.post("/api/auth/register", json=test_user_data)
        
        # Request password reset
        client.post("/api/auth/request-password-reset", json={
            "email": test_user_data["email"]
        })
        
        # Get the reset token
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        reset_token = user.reset_token
        db.close()
        
        # Reset password
        response = client.post("/api/auth/reset-password", json={
            "token": reset_token,
            "new_password": "NewPassword123"
        })
        assert response.status_code == 200
        
        # Verify token is cleared
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        assert user.reset_token is None
        assert user.reset_token_expires is None
        db.close()
        
        # Try to use the same token again
        response = client.post("/api/auth/reset-password", json={
            "token": reset_token,
            "new_password": "AnotherPassword123"
        })
        assert response.status_code == 400

class TestEmailVerification:
    def test_email_verification_flow(self, client, test_user_data):
        """Test the email verification flow."""
        # Register user
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["is_verified"] == False
        
        # Get verification token from database
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        verification_token = user.verification_token
        assert verification_token is not None
        db.close()
        
        # Verify email
        response = client.post("/api/auth/verify-email", json={
            "token": verification_token
        })
        assert response.status_code == 200
        assert "Email verified successfully" in response.json()["message"]
        
        # Check that user is now verified
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        assert user.is_verified == True
        assert user.verification_token is None
        assert user.verification_token_expires is None
        db.close()
    
    def test_verify_email_with_invalid_token(self, client):
        """Test email verification with invalid token."""
        response = client.post("/api/auth/verify-email", json={
            "token": "invalid-token"
        })
        assert response.status_code == 400
        assert "Invalid or expired verification token" in response.json()["detail"]
    
    def test_verify_email_with_expired_token(self, client, test_user_data):
        """Test email verification with expired token."""
        # Register user
        client.post("/api/auth/register", json=test_user_data)
        
        # Manually expire the verification token
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        verification_token = user.verification_token
        user.verification_token_expires = datetime.utcnow() - timedelta(hours=1)  # Expired
        db.commit()
        db.close()
        
        # Try to verify with expired token
        response = client.post("/api/auth/verify-email", json={
            "token": verification_token
        })
        assert response.status_code == 400
        assert "Invalid or expired verification token" in response.json()["detail"]

if __name__ == "__main__":
    pytest.main([__file__])
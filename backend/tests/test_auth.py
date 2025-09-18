import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.core.auth import get_password_hash
from main import app
import tempfile
import os

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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

@pytest.fixture
def test_teacher_data():
    return {
        "email": "teacher@example.com",
        "password": "TeacherPass123",
        "first_name": "Test",
        "last_name": "Teacher",
        "role": "teacher"
    }

class TestUserRegistration:
    def test_register_user_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["first_name"] == test_user_data["first_name"]
        assert data["role"] == test_user_data["role"]
        assert "id" in data
        assert data["is_active"] == True
        assert data["is_verified"] == False
    
    def test_register_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email."""
        # Register first user
        client.post("/api/auth/register", json=test_user_data)
        
        # Try to register with same email
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_invalid_password(self, client, test_user_data):
        """Test registration with invalid password."""
        test_user_data["password"] = "weak"
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 422
    
    def test_register_invalid_email(self, client, test_user_data):
        """Test registration with invalid email."""
        test_user_data["email"] = "invalid-email"
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 422

class TestUserLogin:
    def test_login_success(self, client, test_user_data):
        """Test successful login."""
        # Register user first
        client.post("/api/auth/register", json=test_user_data)
        
        # Login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
    
    def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password."""
        # Register user first
        client.post("/api/auth/register", json=test_user_data)
        
        # Login with wrong password
        login_data = {
            "email": test_user_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401

class TestUserProfile:
    def test_get_current_user(self, client, test_user_data):
        """Test getting current user information."""
        # Register and login
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 403
    
    def test_update_current_user(self, client, test_user_data):
        """Test updating current user information."""
        # Register and login
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Update user
        headers = {"Authorization": f"Bearer {token}"}
        update_data = {"first_name": "Updated"}
        response = client.put("/api/auth/me", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"

class TestRoleBasedAccess:
    def test_teacher_can_list_users(self, client, test_teacher_data, test_user_data):
        """Test that teachers can list users."""
        # Register teacher and student
        client.post("/api/auth/register", json=test_teacher_data)
        client.post("/api/auth/register", json=test_user_data)
        
        # Login as teacher
        login_response = client.post("/api/auth/login", json={
            "email": test_teacher_data["email"],
            "password": test_teacher_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # List users
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/users", headers=headers)
        
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 2  # At least teacher and student
    
    def test_student_cannot_list_users(self, client, test_user_data):
        """Test that students cannot list users."""
        # Register and login as student
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Try to list users
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/users", headers=headers)
        
        assert response.status_code == 403

class TestPasswordReset:
    def test_request_password_reset(self, client, test_user_data):
        """Test password reset request."""
        # Register user first
        client.post("/api/auth/register", json=test_user_data)
        
        # Request password reset
        response = client.post("/api/auth/request-password-reset", json={
            "email": test_user_data["email"]
        })
        
        assert response.status_code == 200
        assert "password reset link" in response.json()["message"]
    
    def test_request_password_reset_nonexistent_email(self, client):
        """Test password reset request for nonexistent email."""
        response = client.post("/api/auth/request-password-reset", json={
            "email": "nonexistent@example.com"
        })
        
        # Should still return success for security
        assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__])
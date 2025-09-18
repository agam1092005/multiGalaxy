"""
Tests for analytics API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.models.analytics import InteractionType
from app.models.user import User, UserRole


@pytest.fixture
def mock_analytics_service():
    """Mock analytics service for testing"""
    with patch('app.api.analytics.analytics_service') as mock:
        yield mock


@pytest.fixture
def sample_user():
    """Create sample user for testing"""
    return User(
        id=str(uuid4()),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.STUDENT
    )


@pytest.fixture
def sample_parent_user():
    """Create sample parent user for testing"""
    return User(
        id=str(uuid4()),
        email="parent@example.com",
        first_name="Parent",
        last_name="User",
        role=UserRole.PARENT
    )


class TestAnalyticsAPI:
    """Test analytics API endpoints"""
    
    def test_get_user_analytics_success(self, client: TestClient, mock_analytics_service, sample_user):
        """Test successful retrieval of user analytics"""
        # Mock authentication
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            # Mock analytics data
            mock_analytics_data = {
                "user_id": sample_user.id,
                "subject": "Mathematics",
                "skill_assessments": [
                    {
                        "skill_name": "algebra",
                        "proficiency": 0.75,
                        "confidence": 0.8,
                        "level": "proficient",
                        "trend": "improving",
                        "evidence_count": 10,
                        "last_assessed": datetime.utcnow().isoformat()
                    }
                ],
                "progress_metrics": {
                    "total_time_spent": 3600,
                    "sessions_completed": 5,
                    "problems_solved": 15,
                    "success_rate": 0.8,
                    "average_session_duration": 720,
                    "streak_days": 3,
                    "subjects_studied": ["Mathematics"],
                    "improvement_rate": 15.0
                },
                "learning_patterns": {
                    "preferred_learning_times": [14, 16, 20],
                    "session_frequency": 4.2,
                    "attention_span": 1800,
                    "difficulty_preference": 0.6,
                    "interaction_preferences": {
                        "problem_solving": 0.6,
                        "drawing": 0.3,
                        "speech_input": 0.1
                    },
                    "common_mistake_patterns": []
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
            mock_analytics_service.get_user_analytics.return_value = mock_analytics_data
            
            response = client.get(f"/api/analytics/user/{sample_user.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == sample_user.id
            assert data["subject"] == "Mathematics"
            assert len(data["skill_assessments"]) == 1
            assert data["progress_metrics"]["success_rate"] == 0.8
    
    def test_get_user_analytics_access_denied(self, client: TestClient, sample_user):
        """Test access denied for unauthorized user"""
        other_user = User(
            id=str(uuid4()),
            email="other@example.com",
            first_name="Other",
            last_name="User",
            role=UserRole.STUDENT
        )
        
        with patch('app.api.analytics.get_current_user', return_value=other_user):
            response = client.get(f"/api/analytics/user/{sample_user.id}")
            
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]
    
    def test_get_user_analytics_not_found(self, client: TestClient, mock_analytics_service, sample_user):
        """Test analytics not found"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            mock_analytics_service.get_user_analytics.return_value = None
            
            response = client.get(f"/api/analytics/user/{sample_user.id}")
            
            assert response.status_code == 404
            assert "No analytics data found" in response.json()["detail"]
    
    def test_get_user_recommendations_success(self, client: TestClient, mock_analytics_service, sample_user):
        """Test successful retrieval of user recommendations"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            mock_recommendations = [
                {
                    "type": "skill_focus",
                    "title": "Practice Algebra",
                    "description": "Focus on algebraic equations",
                    "priority": 1,
                    "estimated_time": 20,
                    "skills_targeted": ["algebra"],
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
            
            mock_analytics_service.generate_recommendations.return_value = mock_recommendations
            
            response = client.get(f"/api/analytics/user/{sample_user.id}/recommendations")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["type"] == "skill_focus"
            assert data[0]["priority"] == 1
    
    def test_record_user_interaction_success(self, client: TestClient, mock_analytics_service, sample_user):
        """Test successful recording of user interaction"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            mock_interaction = MagicMock()
            mock_interaction.id = uuid4()
            mock_analytics_service.record_interaction.return_value = mock_interaction
            
            interaction_data = {
                "session_id": str(uuid4()),
                "interaction_type": "problem_solving",
                "subject": "Mathematics",
                "skill_tags": ["algebra", "equations"],
                "success_rate": 0.8,
                "time_spent": 300,
                "difficulty_level": 0.6
            }
            
            response = client.post(
                f"/api/analytics/user/{sample_user.id}/interaction",
                params=interaction_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "Interaction recorded successfully" in data["message"]
            assert "interaction_id" in data
    
    def test_record_user_interaction_invalid_success_rate(self, client: TestClient, sample_user):
        """Test recording interaction with invalid success rate"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            interaction_data = {
                "session_id": str(uuid4()),
                "interaction_type": "problem_solving",
                "subject": "Mathematics",
                "skill_tags": ["algebra"],
                "success_rate": 1.5,  # Invalid: > 1.0
                "time_spent": 300
            }
            
            response = client.post(
                f"/api/analytics/user/{sample_user.id}/interaction",
                params=interaction_data
            )
            
            assert response.status_code == 400
            assert "Success rate must be between 0.0 and 1.0" in response.json()["detail"]
    
    def test_record_user_interaction_access_denied(self, client: TestClient, sample_user):
        """Test access denied for recording interaction"""
        other_user = User(
            id=str(uuid4()),
            email="other@example.com",
            first_name="Other",
            last_name="User",
            role=UserRole.STUDENT
        )
        
        with patch('app.api.analytics.get_current_user', return_value=other_user):
            interaction_data = {
                "session_id": str(uuid4()),
                "interaction_type": "problem_solving",
                "subject": "Mathematics",
                "skill_tags": ["algebra"],
                "success_rate": 0.8,
                "time_spent": 300
            }
            
            response = client.post(
                f"/api/analytics/user/{sample_user.id}/interaction",
                params=interaction_data
            )
            
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]
    
    def test_generate_progress_report_success(self, client: TestClient, mock_analytics_service, sample_user):
        """Test successful progress report generation"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            mock_report = {
                "id": str(uuid4()),
                "report_type": "weekly",
                "period_start": datetime.utcnow().isoformat(),
                "period_end": datetime.utcnow().isoformat(),
                "summary_data": {
                    "total_study_time": 3600,
                    "sessions_completed": 5,
                    "success_rate": 0.8,
                    "improvement_rate": 15.0
                },
                "recommendations": [],
                "generated_at": datetime.utcnow().isoformat()
            }
            
            mock_analytics_service.generate_progress_report.return_value = mock_report
            
            response = client.get(f"/api/analytics/user/{sample_user.id}/progress-report")
            
            assert response.status_code == 200
            data = response.json()
            assert data["report_type"] == "weekly"
            assert data["summary_data"]["success_rate"] == 0.8
    
    def test_generate_progress_report_invalid_type(self, client: TestClient, sample_user):
        """Test progress report with invalid report type"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            response = client.get(
                f"/api/analytics/user/{sample_user.id}/progress-report",
                params={"report_type": "invalid_type"}
            )
            
            assert response.status_code == 422  # Validation error
    
    def test_get_parent_dashboard_success(self, client: TestClient, mock_analytics_service, sample_parent_user):
        """Test successful parent dashboard retrieval"""
        with patch('app.api.analytics.get_current_user', return_value=sample_parent_user):
            child_ids = [str(uuid4()), str(uuid4())]
            
            mock_dashboard_data = {
                "children": [
                    {
                        "user_id": child_ids[0],
                        "name": "Child One",
                        "weekly_progress": {
                            "total_time_spent": 1800,
                            "sessions_completed": 3,
                            "problems_solved": 8,
                            "success_rate": 0.75,
                            "average_session_duration": 600,
                            "streak_days": 2,
                            "subjects_studied": ["Mathematics"],
                            "improvement_rate": 10.0
                        },
                        "current_streak": 2,
                        "subjects_studied": ["Mathematics"],
                        "recent_activity": [],
                        "alerts": []
                    }
                ],
                "summary": {
                    "total_study_time": 3600,
                    "total_sessions": 6,
                    "average_success_rate": 0.75,
                    "active_children": 2
                }
            }
            
            mock_analytics_service.get_parent_dashboard_data.return_value = mock_dashboard_data
            
            response = client.get(
                "/api/analytics/parent-dashboard",
                params={"child_user_ids": child_ids}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["children"]) == 1
            assert data["summary"]["active_children"] == 2
    
    def test_get_parent_dashboard_access_denied(self, client: TestClient, sample_user):
        """Test parent dashboard access denied for non-parent"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            response = client.get(
                "/api/analytics/parent-dashboard",
                params={"child_user_ids": [str(uuid4())]}
            )
            
            assert response.status_code == 403
            assert "Only parents can access" in response.json()["detail"]
    
    def test_get_learning_insights_success(self, client: TestClient, mock_analytics_service, sample_user):
        """Test successful learning insights retrieval"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            mock_analytics = MagicMock()
            mock_analytics.learning_patterns.interaction_preferences = {"drawing": 0.4}
            mock_analytics.learning_patterns.attention_span = 1800
            mock_analytics.learning_patterns.preferred_learning_times = [14, 16]
            mock_analytics.learning_patterns.session_frequency = 4.0
            mock_analytics.progress_metrics.success_rate = 0.85
            mock_analytics.skill_assessments = [
                MagicMock(skill_name="algebra", proficiency=0.9, trend="improving"),
                MagicMock(skill_name="geometry", proficiency=0.7, trend="stable"),
                MagicMock(skill_name="calculus", proficiency=0.5, trend="improving")
            ]
            
            mock_analytics_service.get_user_analytics.return_value = mock_analytics
            
            response = client.get(f"/api/analytics/user/{sample_user.id}/learning-insights")
            
            assert response.status_code == 200
            data = response.json()
            assert "learning_style" in data
            assert "optimal_session_length" in data
            assert "best_study_times" in data
            assert "consistency_score" in data
            assert "challenge_readiness" in data
            assert "areas_of_strength" in data
            assert "growth_opportunities" in data
    
    def test_get_learning_insights_no_data(self, client: TestClient, mock_analytics_service, sample_user):
        """Test learning insights when no analytics data exists"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            mock_analytics_service.get_user_analytics.return_value = None
            
            response = client.get(f"/api/analytics/user/{sample_user.id}/learning-insights")
            
            assert response.status_code == 404
            assert "No analytics data found" in response.json()["detail"]
    
    def test_get_skill_trends_placeholder(self, client: TestClient, sample_user):
        """Test skill trends endpoint (placeholder implementation)"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            response = client.get(
                f"/api/analytics/user/{sample_user.id}/skill-trends",
                params={
                    "subject": "Mathematics",
                    "skill_name": "algebra",
                    "days": 30
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "Skill trends endpoint" in data["message"]
            assert data["user_id"] == sample_user.id
            assert data["subject"] == "Mathematics"
            assert data["skill_name"] == "algebra"
            assert data["days"] == 30


class TestAnalyticsAPIValidation:
    """Test API input validation and error handling"""
    
    def test_invalid_uuid_format(self, client: TestClient, sample_user):
        """Test API with invalid UUID format"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            response = client.get("/api/analytics/user/invalid-uuid")
            
            assert response.status_code == 422  # Validation error
    
    def test_negative_time_spent(self, client: TestClient, sample_user):
        """Test recording interaction with negative time spent"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            interaction_data = {
                "session_id": str(uuid4()),
                "interaction_type": "problem_solving",
                "subject": "Mathematics",
                "skill_tags": ["algebra"],
                "time_spent": -100  # Invalid: negative time
            }
            
            response = client.post(
                f"/api/analytics/user/{sample_user.id}/interaction",
                params=interaction_data
            )
            
            # Should be handled by Pydantic validation or business logic
            assert response.status_code in [400, 422]
    
    def test_empty_skill_tags(self, client: TestClient, mock_analytics_service, sample_user):
        """Test recording interaction with empty skill tags"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            mock_interaction = MagicMock()
            mock_interaction.id = uuid4()
            mock_analytics_service.record_interaction.return_value = mock_interaction
            
            interaction_data = {
                "session_id": str(uuid4()),
                "interaction_type": "problem_solving",
                "subject": "Mathematics",
                "skill_tags": [],  # Empty list should be allowed
                "success_rate": 0.8,
                "time_spent": 300
            }
            
            response = client.post(
                f"/api/analytics/user/{sample_user.id}/interaction",
                params=interaction_data
            )
            
            assert response.status_code == 200
    
    def test_invalid_difficulty_level(self, client: TestClient, sample_user):
        """Test recording interaction with invalid difficulty level"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            interaction_data = {
                "session_id": str(uuid4()),
                "interaction_type": "problem_solving",
                "subject": "Mathematics",
                "skill_tags": ["algebra"],
                "difficulty_level": 1.5  # Invalid: > 1.0
            }
            
            response = client.post(
                f"/api/analytics/user/{sample_user.id}/interaction",
                params=interaction_data
            )
            
            assert response.status_code == 400
            assert "Difficulty level must be between 0.0 and 1.0" in response.json()["detail"]
    
    def test_invalid_ai_feedback_quality(self, client: TestClient, sample_user):
        """Test recording interaction with invalid AI feedback quality"""
        with patch('app.api.analytics.get_current_user', return_value=sample_user):
            interaction_data = {
                "session_id": str(uuid4()),
                "interaction_type": "problem_solving",
                "subject": "Mathematics",
                "skill_tags": ["algebra"],
                "ai_feedback_quality": -0.1  # Invalid: < 0.0
            }
            
            response = client.post(
                f"/api/analytics/user/{sample_user.id}/interaction",
                params=interaction_data
            )
            
            assert response.status_code == 400
            assert "AI feedback quality must be between 0.0 and 1.0" in response.json()["detail"]
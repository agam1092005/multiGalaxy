"""
Tests for analytics service functionality.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.analytics_service import AnalyticsService
from app.services.skill_assessment import SkillAssessmentEngine, ProgressTracker
from app.models.analytics import (
    LearningAnalytics, SkillAssessment, UserInteraction, 
    InteractionType, SkillLevel, TrendDirection
)
from app.models.user import User
from app.models.learning_session import LearningSession


@pytest.fixture
def analytics_service():
    """Create analytics service instance for testing"""
    return AnalyticsService()


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def sample_user():
    """Create sample user for testing"""
    return User(
        id=str(uuid4()),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role="student"
    )


@pytest.fixture
def sample_learning_session(sample_user):
    """Create sample learning session"""
    return LearningSession(
        id=uuid4(),
        user_id=sample_user.id,
        subject="Mathematics",
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow()
    )


@pytest.fixture
def sample_interactions(sample_learning_session):
    """Create sample user interactions"""
    interactions = []
    for i in range(5):
        interaction = UserInteraction(
            id=uuid4(),
            session_id=sample_learning_session.id,
            interaction_type=InteractionType.PROBLEM_SOLVING.value,
            subject="Mathematics",
            skill_tags=["algebra", "equations"],
            success_rate=0.8 + (i * 0.05),  # Improving trend
            time_spent=300 + (i * 60),
            difficulty_level=0.5,
            timestamp=datetime.utcnow() - timedelta(days=i)
        )
        interactions.append(interaction)
    return interactions


class TestSkillAssessmentEngine:
    """Test skill assessment algorithms"""
    
    @pytest.mark.asyncio
    async def test_assess_user_skills_empty_interactions(self, mock_db):
        """Test skill assessment with no interactions"""
        engine = SkillAssessmentEngine()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = await engine.assess_user_skills(mock_db, uuid4(), "Mathematics")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_assess_user_skills_insufficient_data(self, mock_db, sample_interactions):
        """Test skill assessment with insufficient interaction data"""
        engine = SkillAssessmentEngine()
        # Only provide 2 interactions (less than minimum of 5)
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_interactions[:2]
        
        result = await engine.assess_user_skills(mock_db, uuid4(), "Mathematics")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_assess_user_skills_sufficient_data(self, mock_db, sample_interactions):
        """Test skill assessment with sufficient interaction data"""
        engine = SkillAssessmentEngine()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_interactions
        
        result = await engine.assess_user_skills(mock_db, uuid4(), "Mathematics")
        
        # Should have assessments for skills in the interactions
        assert "algebra" in result
        assert "equations" in result
        
        # Check assessment properties
        algebra_assessment = result["algebra"]
        assert 0.0 <= algebra_assessment.proficiency <= 1.0
        assert 0.0 <= algebra_assessment.confidence <= 1.0
        assert algebra_assessment.skill_name == "algebra"
        assert algebra_assessment.evidence_count == len(sample_interactions)
    
    def test_calculate_proficiency_improving_trend(self):
        """Test proficiency calculation with improving performance"""
        engine = SkillAssessmentEngine()
        
        # Create interactions with improving success rates
        interactions = []
        for i in range(5):
            interaction = MagicMock()
            interaction.interaction_type = InteractionType.PROBLEM_SOLVING.value
            interaction.success_rate = 0.5 + (i * 0.1)  # 0.5 to 0.9
            interaction.difficulty_level = 0.5
            interaction.timestamp = datetime.utcnow() - timedelta(days=i)
            interactions.append(interaction)
        
        proficiency = engine._calculate_proficiency(interactions)
        
        # Should be weighted toward more recent (better) performance
        assert 0.6 < proficiency <= 1.0
    
    def test_determine_skill_level(self):
        """Test skill level determination based on proficiency"""
        engine = SkillAssessmentEngine()
        
        assert engine._determine_skill_level(0.95) == SkillLevel.MASTERY
        assert engine._determine_skill_level(0.8) == SkillLevel.ADVANCED
        assert engine._determine_skill_level(0.65) == SkillLevel.PROFICIENT
        assert engine._determine_skill_level(0.5) == SkillLevel.DEVELOPING
        assert engine._determine_skill_level(0.3) == SkillLevel.BEGINNER
    
    def test_calculate_trend_improving(self):
        """Test trend calculation for improving performance"""
        engine = SkillAssessmentEngine()
        
        # Create interactions with improving trend
        interactions = []
        for i in range(10):
            interaction = MagicMock()
            # First half: 0.4-0.5, Second half: 0.7-0.8
            interaction.success_rate = 0.4 + (0.1 if i < 5 else 0.3) + (i % 5) * 0.02
            interaction.timestamp = datetime.utcnow() - timedelta(days=9-i)
            interactions.append(interaction)
        
        trend = engine._calculate_trend(interactions)
        assert trend == TrendDirection.IMPROVING
    
    def test_calculate_trend_declining(self):
        """Test trend calculation for declining performance"""
        engine = SkillAssessmentEngine()
        
        # Create interactions with declining trend
        interactions = []
        for i in range(10):
            interaction = MagicMock()
            # First half: 0.7-0.8, Second half: 0.4-0.5
            interaction.success_rate = 0.7 - (0.3 if i >= 5 else 0) + (i % 5) * 0.02
            interaction.timestamp = datetime.utcnow() - timedelta(days=9-i)
            interactions.append(interaction)
        
        trend = engine._calculate_trend(interactions)
        assert trend == TrendDirection.DECLINING


class TestProgressTracker:
    """Test progress tracking functionality"""
    
    @pytest.mark.asyncio
    async def test_calculate_progress_metrics_empty(self, mock_db):
        """Test progress metrics calculation with no data"""
        tracker = ProgressTracker()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = await tracker.calculate_progress_metrics(mock_db, uuid4())
        
        expected = tracker._empty_progress_metrics()
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_calculate_progress_metrics_with_data(self, mock_db, sample_interactions):
        """Test progress metrics calculation with interaction data"""
        tracker = ProgressTracker()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_interactions
        
        # Mock additional queries for streak and improvement calculations
        mock_db.query.return_value.join.return_value.filter.return_value.distinct.return_value.order_by.return_value.all.return_value = [
            MagicMock(date=datetime.utcnow().date())
        ]
        
        result = await tracker.calculate_progress_metrics(mock_db, uuid4(), "Mathematics")
        
        assert result["total_time_spent"] > 0
        assert result["sessions_completed"] > 0
        assert 0.0 <= result["success_rate"] <= 1.0
        assert result["subjects_studied"] == ["Mathematics"]
    
    @pytest.mark.asyncio
    async def test_calculate_streak_consecutive_days(self, mock_db):
        """Test streak calculation with consecutive learning days"""
        tracker = ProgressTracker()
        
        # Mock consecutive dates
        dates = []
        for i in range(5):
            date_mock = MagicMock()
            date_mock.date = datetime.utcnow().date() - timedelta(days=i)
            dates.append(date_mock)
        
        mock_db.query.return_value.join.return_value.filter.return_value.distinct.return_value.order_by.return_value.all.return_value = dates
        
        streak = await tracker._calculate_streak(mock_db, uuid4(), "Mathematics")
        
        assert streak == 5


class TestAnalyticsService:
    """Test analytics service functionality"""
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_no_data(self, analytics_service, mock_db):
        """Test getting analytics when no data exists"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await analytics_service.get_user_analytics(mock_db, uuid4(), "Mathematics")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_record_interaction_success(self, analytics_service, mock_db, sample_learning_session):
        """Test recording a user interaction"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_learning_session
        mock_db.add = MagicMock()
        mock_db.flush = MagicMock()
        mock_db.commit = MagicMock()
        
        # Mock skill assessment engine
        analytics_service.skill_engine.update_skill_assessment = AsyncMock()
        
        result = await analytics_service.record_interaction(
            db=mock_db,
            session_id=sample_learning_session.id,
            interaction_type=InteractionType.PROBLEM_SOLVING,
            subject="Mathematics",
            skill_tags=["algebra"],
            success_rate=0.8,
            time_spent=300
        )
        
        assert result is not None
        assert result.interaction_type == InteractionType.PROBLEM_SOLVING.value
        assert result.subject == "Mathematics"
        assert result.skill_tags == ["algebra"]
        assert result.success_rate == 0.8
        assert result.time_spent == 300
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_weak_skills(self, analytics_service, mock_db):
        """Test recommendation generation for users with weak skills"""
        # Mock analytics data with weak skills
        mock_analytics = MagicMock()
        mock_analytics.skill_assessments = [
            MagicMock(skill_name="algebra", proficiency=0.3, level=MagicMock(value="beginner")),
            MagicMock(skill_name="geometry", proficiency=0.5, level=MagicMock(value="developing"))
        ]
        mock_analytics.progress_metrics = MagicMock(success_rate=0.4)
        mock_analytics.learning_patterns = MagicMock(preferred_learning_times=[14])
        
        analytics_service.get_user_analytics = AsyncMock(return_value=mock_analytics)
        
        recommendations = await analytics_service.generate_recommendations(mock_db, uuid4())
        
        assert len(recommendations) > 0
        
        # Should have skill focus recommendations for weak skills
        skill_recommendations = [r for r in recommendations if r.type == "skill_focus"]
        assert len(skill_recommendations) > 0
        
        # Should have difficulty adjustment for low success rate
        difficulty_recommendations = [r for r in recommendations if r.type == "difficulty_adjustment"]
        assert len(difficulty_recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_generate_progress_report(self, analytics_service, mock_db):
        """Test progress report generation"""
        # Mock dependencies
        analytics_service.get_user_analytics = AsyncMock(return_value=MagicMock(
            skill_assessments=[
                MagicMock(skill_name="algebra", proficiency=0.8, level=MagicMock(value="advanced")),
                MagicMock(skill_name="geometry", proficiency=0.4, level=MagicMock(value="developing"))
            ]
        ))
        analytics_service.progress_tracker.calculate_progress_metrics = AsyncMock(return_value={
            "total_time_spent": 3600,
            "sessions_completed": 5,
            "success_rate": 0.75,
            "improvement_rate": 15.0,
            "streak_days": 3,
            "subjects_studied": ["Mathematics"]
        })
        analytics_service.generate_recommendations = AsyncMock(return_value=[])
        
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        
        report = await analytics_service.generate_progress_report(mock_db, uuid4())
        
        assert report is not None
        assert report.report_type == "weekly"
        assert report.summary_data["total_study_time"] == 3600
        assert report.summary_data["sessions_completed"] == 5
        assert report.summary_data["success_rate"] == 0.75
        assert len(report.summary_data["top_skills"]) > 0
        assert len(report.summary_data["areas_for_improvement"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_parent_dashboard_data(self, analytics_service, mock_db):
        """Test parent dashboard data generation"""
        child_ids = [uuid4(), uuid4()]
        
        # Mock user queries
        mock_users = [
            MagicMock(id=child_ids[0], email="child1@example.com"),
            MagicMock(id=child_ids[1], email="child2@example.com")
        ]
        mock_db.query.return_value.filter.return_value.first.side_effect = mock_users
        
        # Mock analytics and progress data
        analytics_service.get_user_analytics = AsyncMock(return_value=MagicMock(
            skill_assessments=[
                MagicMock(proficiency=0.9),
                MagicMock(proficiency=0.6),
                MagicMock(proficiency=0.3)
            ]
        ))
        analytics_service.progress_tracker.calculate_progress_metrics = AsyncMock(return_value={
            "total_time_spent": 1800,
            "sessions_completed": 3,
            "success_rate": 0.8,
            "streak_days": 2,
            "subjects_studied": ["Mathematics"]
        })
        analytics_service._get_recent_activity = AsyncMock(return_value=[])
        analytics_service._generate_parent_alerts = AsyncMock(return_value=[])
        
        dashboard_data = await analytics_service.get_parent_dashboard_data(
            mock_db, uuid4(), child_ids
        )
        
        assert dashboard_data is not None
        assert len(dashboard_data["children"]) == 2
        assert dashboard_data["summary"]["total_study_time"] == 3600  # 1800 * 2
        assert dashboard_data["summary"]["total_sessions"] == 6  # 3 * 2
        assert dashboard_data["summary"]["active_children"] == 2
        
        # Check child data structure
        child_data = dashboard_data["children"][0]
        assert "user_id" in child_data
        assert "name" in child_data
        assert "weekly_progress" in child_data
        assert "skill_summary" in child_data


class TestAnalyticsDataIntegrity:
    """Test data integrity and validation in analytics"""
    
    def test_skill_assessment_validation(self):
        """Test skill assessment data validation"""
        # Valid assessment
        assessment = SkillAssessment(
            skill_name="algebra",
            proficiency=0.75,
            confidence=0.8,
            level=SkillLevel.PROFICIENT.value,
            trend=TrendDirection.IMPROVING.value,
            evidence_count=10
        )
        
        assert 0.0 <= assessment.proficiency <= 1.0
        assert 0.0 <= assessment.confidence <= 1.0
        assert assessment.evidence_count >= 0
    
    def test_interaction_data_validation(self):
        """Test user interaction data validation"""
        interaction = UserInteraction(
            session_id=uuid4(),
            interaction_type=InteractionType.PROBLEM_SOLVING.value,
            subject="Mathematics",
            skill_tags=["algebra", "equations"],
            success_rate=0.85,
            time_spent=420,
            difficulty_level=0.6
        )
        
        assert interaction.success_rate is None or (0.0 <= interaction.success_rate <= 1.0)
        assert 0.0 <= interaction.difficulty_level <= 1.0
        assert interaction.time_spent >= 0
        assert isinstance(interaction.skill_tags, list)
    
    def test_progress_metrics_consistency(self):
        """Test progress metrics data consistency"""
        # Mock progress data
        progress = {
            "total_time_spent": 7200,  # 2 hours
            "sessions_completed": 4,
            "problems_solved": 15,
            "success_rate": 0.8,
            "average_session_duration": 1800,  # 30 minutes
            "streak_days": 5,
            "subjects_studied": ["Mathematics", "Science"],
            "improvement_rate": 12.5
        }
        
        # Validate consistency
        assert progress["total_time_spent"] >= 0
        assert progress["sessions_completed"] >= 0
        assert progress["problems_solved"] >= 0
        assert 0.0 <= progress["success_rate"] <= 1.0
        assert progress["average_session_duration"] >= 0
        assert progress["streak_days"] >= 0
        assert len(progress["subjects_studied"]) >= 0
        
        # Check logical consistency
        if progress["sessions_completed"] > 0:
            expected_avg = progress["total_time_spent"] // progress["sessions_completed"]
            # Allow some tolerance for rounding
            assert abs(progress["average_session_duration"] - expected_avg) <= progress["total_time_spent"] * 0.1
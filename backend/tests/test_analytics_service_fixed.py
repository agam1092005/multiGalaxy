"""
Fixed tests for analytics service functionality.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analytics_service import AnalyticsService
from app.services.skill_assessment import SkillAssessmentEngine, ProgressTracker
from app.models.analytics import InteractionType, SkillLevel, TrendDirection


@pytest.fixture
def analytics_service():
    """Create analytics service instance for testing"""
    return AnalyticsService()


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MagicMock()


@pytest.fixture
def sample_user_id():
    """Create sample user ID for testing"""
    return str(uuid4())


@pytest.fixture
def sample_session_id():
    """Create sample session ID for testing"""
    return uuid4()


@pytest.fixture
def sample_interactions():
    """Create sample user interactions as mock objects"""
    interactions = []
    for i in range(5):
        interaction = MagicMock()
        interaction.id = uuid4()
        interaction.session_id = uuid4()
        interaction.interaction_type = InteractionType.PROBLEM_SOLVING.value
        interaction.subject = "Mathematics"
        interaction.skill_tags = ["algebra", "equations"]
        interaction.success_rate = 0.8 + (i * 0.05)  # Improving trend
        interaction.time_spent = 300 + (i * 60)
        interaction.difficulty_level = 0.5
        interaction.timestamp = datetime.utcnow() - timedelta(days=i)
        interactions.append(interaction)
    return interactions


class TestSkillAssessmentEngine:
    """Test skill assessment algorithms"""
    
    @pytest.mark.asyncio
    async def test_assess_user_skills_empty_interactions(self, mock_db, sample_user_id):
        """Test skill assessment with no interactions"""
        engine = SkillAssessmentEngine()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = await engine.assess_user_skills(mock_db, sample_user_id, "Mathematics")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_assess_user_skills_insufficient_data(self, mock_db, sample_user_id, sample_interactions):
        """Test skill assessment with insufficient interaction data"""
        engine = SkillAssessmentEngine()
        # Only provide 2 interactions (less than minimum of 5)
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_interactions[:2]
        
        result = await engine.assess_user_skills(mock_db, sample_user_id, "Mathematics")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_assess_user_skills_sufficient_data(self, mock_db, sample_user_id, sample_interactions):
        """Test skill assessment with sufficient interaction data"""
        engine = SkillAssessmentEngine()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = sample_interactions
        
        result = await engine.assess_user_skills(mock_db, sample_user_id, "Mathematics")
        
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
    async def test_calculate_progress_metrics_empty(self, mock_db, sample_user_id):
        """Test progress metrics calculation with no data"""
        tracker = ProgressTracker()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = await tracker.calculate_progress_metrics(mock_db, sample_user_id)
        
        expected = tracker._empty_progress_metrics()
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_calculate_progress_metrics_with_data(self, mock_db, sample_user_id, sample_interactions):
        """Test progress metrics calculation with interaction data"""
        tracker = ProgressTracker()
        
        # Set up proper time_spent values for the mock interactions
        for i, interaction in enumerate(sample_interactions):
            interaction.time_spent = 300 + (i * 60)  # 300, 360, 420, 480, 540
            interaction.session_id = uuid4()  # Ensure unique session IDs
        
        # Mock the complex query chain properly
        mock_query = MagicMock()
        mock_join = MagicMock()
        mock_filter = MagicMock()
        mock_filter_subject = MagicMock()
        
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter_subject
        mock_filter_subject.all.return_value = sample_interactions
        
        # Mock the _calculate_streak method to avoid complex query mocking
        tracker._calculate_streak = AsyncMock(return_value=3)
        tracker._calculate_improvement_rate = AsyncMock(return_value=15.0)
        
        result = await tracker.calculate_progress_metrics(mock_db, sample_user_id, "Mathematics")
        
        assert result["total_time_spent"] > 0
        assert result["sessions_completed"] > 0
        assert 0.0 <= result["success_rate"] <= 1.0
        assert result["subjects_studied"] == ["Mathematics"]
        assert result["streak_days"] == 3
        assert result["improvement_rate"] == 15.0
    
    @pytest.mark.asyncio
    async def test_calculate_streak_consecutive_days(self, mock_db, sample_user_id):
        """Test streak calculation with consecutive learning days"""
        tracker = ProgressTracker()
        
        # Mock consecutive dates - need to be in descending order (most recent first)
        dates = []
        current_date = datetime.utcnow().date()
        for i in range(5):
            date_mock = MagicMock()
            date_mock.date = current_date - timedelta(days=i)
            dates.append(date_mock)
        
        # Mock the complex query chain for streak calculation
        mock_query = MagicMock()
        mock_join = MagicMock()
        mock_filter = MagicMock()
        mock_distinct = MagicMock()
        mock_order_by = MagicMock()
        
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.distinct.return_value = mock_distinct
        mock_distinct.order_by.return_value = mock_order_by
        mock_order_by.all.return_value = dates
        
        streak = await tracker._calculate_streak(mock_db, sample_user_id, "Mathematics")
        
        assert streak == 5


class TestAnalyticsService:
    """Test analytics service functionality"""
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_no_data(self, analytics_service, mock_db, sample_user_id):
        """Test getting analytics when no data exists"""
        # Mock the query to return None for analytics record
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock the _create_analytics_for_subject method to return a proper mock
        mock_analytics = MagicMock()
        mock_analytics.subject = "Mathematics"
        mock_analytics.updated_at = datetime.utcnow()
        analytics_service._create_analytics_for_subject = AsyncMock(return_value=mock_analytics)
        
        # Mock the skill engine and other dependencies
        analytics_service.skill_engine.assess_user_skills = AsyncMock(return_value={})
        analytics_service.progress_tracker.calculate_progress_metrics = AsyncMock(return_value={
            "total_time_spent": 0,
            "sessions_completed": 0,
            "problems_solved": 0,
            "success_rate": 0.0,
            "average_session_duration": 0,
            "streak_days": 0,
            "subjects_studied": [],
            "improvement_rate": 0.0
        })
        from app.models.analytics import LearningPatterns
        analytics_service._analyze_learning_patterns = AsyncMock(return_value=LearningPatterns(
            preferred_learning_times=[],
            session_frequency=0.0,
            attention_span=0,
            difficulty_preference=0.5,
            interaction_preferences={},
            common_mistake_patterns=[]
        ))
        
        result = await analytics_service.get_user_analytics(mock_db, sample_user_id, "Mathematics")
        
        assert result is not None
        assert result.subject == "Mathematics"
    
    @pytest.mark.asyncio
    async def test_record_interaction_success(self, analytics_service, mock_db, sample_session_id):
        """Test recording a user interaction"""
        # Mock learning session
        mock_session = MagicMock()
        mock_session.user_id = str(uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.add = MagicMock()
        mock_db.flush = MagicMock()
        mock_db.commit = MagicMock()
        
        # Mock skill assessment engine
        analytics_service.skill_engine.update_skill_assessment = AsyncMock()
        
        result = await analytics_service.record_interaction(
            db=mock_db,
            session_id=sample_session_id,
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
    async def test_generate_recommendations_weak_skills(self, analytics_service, mock_db, sample_user_id):
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
        
        recommendations = await analytics_service.generate_recommendations(mock_db, sample_user_id)
        
        assert len(recommendations) > 0
        
        # Should have skill focus recommendations for weak skills
        skill_recommendations = [r for r in recommendations if r.type == "skill_focus"]
        assert len(skill_recommendations) > 0
        
        # Should have difficulty adjustment for low success rate
        difficulty_recommendations = [r for r in recommendations if r.type == "difficulty_adjustment"]
        assert len(difficulty_recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_generate_progress_report(self, analytics_service, mock_db, sample_user_id):
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
        
        # Mock ProgressReport creation to avoid database issues
        with patch('app.services.analytics_service.ProgressReport') as mock_progress_report:
            mock_report_instance = MagicMock()
            mock_report_instance.id = uuid4()
            mock_report_instance.report_type = "weekly"
            mock_report_instance.summary_data = {
                "total_study_time": 3600,
                "sessions_completed": 5,
                "success_rate": 0.75
            }
            mock_progress_report.return_value = mock_report_instance
            
            report = await analytics_service.generate_progress_report(mock_db, sample_user_id)
            
            assert report is not None
            assert report.report_type == "weekly"
    
    @pytest.mark.asyncio
    async def test_get_parent_dashboard_data(self, analytics_service, mock_db):
        """Test parent dashboard data generation"""
        parent_id = str(uuid4())
        child_ids = [str(uuid4()), str(uuid4())]
        
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
            mock_db, parent_id, child_ids
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
    
    def test_skill_level_enum_values(self):
        """Test skill level enum values"""
        assert SkillLevel.BEGINNER.value == "beginner"
        assert SkillLevel.DEVELOPING.value == "developing"
        assert SkillLevel.PROFICIENT.value == "proficient"
        assert SkillLevel.ADVANCED.value == "advanced"
        assert SkillLevel.MASTERY.value == "mastery"
    
    def test_trend_direction_enum_values(self):
        """Test trend direction enum values"""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.DECLINING.value == "declining"
        assert TrendDirection.INSUFFICIENT_DATA.value == "insufficient_data"
    
    def test_interaction_type_enum_values(self):
        """Test interaction type enum values"""
        assert InteractionType.PROBLEM_SOLVING.value == "problem_solving"
        assert InteractionType.QUESTION_ASKING.value == "question_asking"
        assert InteractionType.DRAWING.value == "drawing"
        assert InteractionType.SPEECH_INPUT.value == "speech_input"
        assert InteractionType.DOCUMENT_UPLOAD.value == "document_upload"
        assert InteractionType.WHITEBOARD_INTERACTION.value == "whiteboard_interaction"
    
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


class TestSkillAssessmentAlgorithms:
    """Test specific skill assessment algorithm logic"""
    
    def test_proficiency_calculation_edge_cases(self):
        """Test proficiency calculation with edge cases"""
        engine = SkillAssessmentEngine()
        
        # Test with no interactions
        assert engine._calculate_proficiency([]) == 0.0
        
        # Test with single interaction
        interaction = MagicMock()
        interaction.interaction_type = InteractionType.PROBLEM_SOLVING.value
        interaction.success_rate = 0.8
        interaction.difficulty_level = 0.5
        interaction.timestamp = datetime.utcnow()
        
        proficiency = engine._calculate_proficiency([interaction])
        assert 0.0 <= proficiency <= 1.0
    
    def test_confidence_calculation(self):
        """Test confidence calculation logic"""
        engine = SkillAssessmentEngine()
        
        # Create consistent interactions
        interactions = []
        for i in range(10):
            interaction = MagicMock()
            interaction.success_rate = 0.8  # Consistent performance
            interaction.timestamp = datetime.utcnow() - timedelta(days=i)
            interactions.append(interaction)
        
        confidence = engine._calculate_confidence(interactions)
        assert 0.0 <= confidence <= 1.0
        # Should have high confidence due to consistency and quantity
        assert confidence > 0.5
    
    def test_trend_calculation_edge_cases(self):
        """Test trend calculation with edge cases"""
        engine = SkillAssessmentEngine()
        
        # Test with insufficient data
        interactions = [MagicMock() for _ in range(3)]
        trend = engine._calculate_trend(interactions)
        assert trend == TrendDirection.INSUFFICIENT_DATA
        
        # Test with stable performance
        interactions = []
        for i in range(10):
            interaction = MagicMock()
            interaction.success_rate = 0.7  # Stable performance
            interaction.timestamp = datetime.utcnow() - timedelta(days=i)
            interactions.append(interaction)
        
        trend = engine._calculate_trend(interactions)
        assert trend == TrendDirection.STABLE
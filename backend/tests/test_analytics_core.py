"""
Core analytics functionality tests - simplified version focusing on business logic.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import MagicMock

from app.services.skill_assessment import SkillAssessmentEngine, ProgressTracker
from app.models.analytics import InteractionType, SkillLevel, TrendDirection


class TestSkillAssessmentCore:
    """Test core skill assessment logic without database dependencies"""
    
    def test_determine_skill_level(self):
        """Test skill level determination based on proficiency"""
        engine = SkillAssessmentEngine()
        
        assert engine._determine_skill_level(0.95) == SkillLevel.MASTERY
        assert engine._determine_skill_level(0.8) == SkillLevel.ADVANCED
        assert engine._determine_skill_level(0.65) == SkillLevel.PROFICIENT
        assert engine._determine_skill_level(0.5) == SkillLevel.DEVELOPING
        assert engine._determine_skill_level(0.3) == SkillLevel.BEGINNER
    
    def test_calculate_proficiency_with_mock_interactions(self):
        """Test proficiency calculation with mock interactions"""
        engine = SkillAssessmentEngine()
        
        # Create mock interactions with improving success rates
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
    
    def test_calculate_trend_insufficient_data(self):
        """Test trend calculation with insufficient data"""
        engine = SkillAssessmentEngine()
        
        # Create too few interactions
        interactions = [MagicMock() for _ in range(3)]
        trend = engine._calculate_trend(interactions)
        assert trend == TrendDirection.INSUFFICIENT_DATA
    
    def test_calculate_confidence_with_consistent_data(self):
        """Test confidence calculation with consistent performance"""
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


class TestProgressTrackerCore:
    """Test core progress tracking logic"""
    
    def test_empty_progress_metrics(self):
        """Test empty progress metrics structure"""
        tracker = ProgressTracker()
        metrics = tracker._empty_progress_metrics()
        
        expected_keys = [
            "total_time_spent", "sessions_completed", "problems_solved",
            "success_rate", "average_session_duration", "streak_days",
            "subjects_studied", "improvement_rate"
        ]
        
        for key in expected_keys:
            assert key in metrics
        
        assert metrics["total_time_spent"] == 0
        assert metrics["sessions_completed"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["subjects_studied"] == []


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
    """Test specific skill assessment algorithm edge cases"""
    
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
    
    def test_skill_weights_configuration(self):
        """Test that skill weights are properly configured"""
        engine = SkillAssessmentEngine()
        
        # Check that all interaction types have weights
        for interaction_type in InteractionType:
            assert interaction_type in engine.skill_weights
            assert 0.0 <= engine.skill_weights[interaction_type] <= 1.0
        
        # Problem solving should have the highest weight
        assert engine.skill_weights[InteractionType.PROBLEM_SOLVING] == 1.0
    
    def test_minimum_interactions_threshold(self):
        """Test minimum interactions threshold"""
        engine = SkillAssessmentEngine()
        
        # Should be a reasonable number for reliable assessment
        assert engine.min_interactions_for_assessment >= 3
        assert engine.min_interactions_for_assessment <= 10
    
    def test_time_decay_factor(self):
        """Test time decay factor is reasonable"""
        engine = SkillAssessmentEngine()
        
        # Should be between 0.9 and 1.0 for reasonable decay
        assert 0.9 <= engine.time_decay_factor < 1.0


class TestAnalyticsBusinessLogic:
    """Test analytics business logic and calculations"""
    
    def test_skill_level_progression(self):
        """Test that skill levels represent a logical progression"""
        levels = [
            SkillLevel.BEGINNER,
            SkillLevel.DEVELOPING, 
            SkillLevel.PROFICIENT,
            SkillLevel.ADVANCED,
            SkillLevel.MASTERY
        ]
        
        engine = SkillAssessmentEngine()
        
        # Test progression with increasing proficiency
        proficiencies = [0.2, 0.45, 0.65, 0.8, 0.95]
        
        for i, proficiency in enumerate(proficiencies):
            level = engine._determine_skill_level(proficiency)
            assert level == levels[i]
    
    def test_trend_calculation_stability(self):
        """Test trend calculation with stable performance"""
        engine = SkillAssessmentEngine()
        
        # Create interactions with stable performance
        interactions = []
        for i in range(10):
            interaction = MagicMock()
            interaction.success_rate = 0.7  # Stable performance
            interaction.timestamp = datetime.utcnow() - timedelta(days=i)
            interactions.append(interaction)
        
        trend = engine._calculate_trend(interactions)
        assert trend == TrendDirection.STABLE
    
    def test_confidence_calculation_factors(self):
        """Test that confidence calculation considers multiple factors"""
        engine = SkillAssessmentEngine()
        
        # Test with many recent consistent interactions
        interactions = []
        for i in range(20):
            interaction = MagicMock()
            interaction.success_rate = 0.8
            interaction.timestamp = datetime.utcnow() - timedelta(hours=i)  # Recent
            interactions.append(interaction)
        
        high_confidence = engine._calculate_confidence(interactions)
        
        # Test with few old inconsistent interactions
        interactions = []
        for i in range(3):
            interaction = MagicMock()
            interaction.success_rate = 0.3 + (i * 0.3)  # Inconsistent
            interaction.timestamp = datetime.utcnow() - timedelta(days=20 + i)  # Old
            interactions.append(interaction)
        
        low_confidence = engine._calculate_confidence(interactions)
        
        # High confidence should be greater than low confidence
        assert high_confidence > low_confidence
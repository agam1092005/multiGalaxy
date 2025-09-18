"""
Integration tests for AI Reasoning API endpoints

Tests the REST API endpoints for AI-powered educational interactions,
ensuring proper request/response handling and error management.
"""

import pytest
import json
import os
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app
from app.services.ai_reasoning_engine import (
    AIResponse,
    FeedbackType,
    LearningLevel,
    SubjectArea
)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["GEMINI_API_KEY"] = "test-key"

client = TestClient(app)

class TestAIReasoningAPI:
    """Test suite for AI Reasoning API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {"user_id": "test-user-123", "email": "test@example.com"}
    
    @pytest.fixture
    def sample_multimodal_request(self):
        """Sample multimodal input request"""
        return {
            "session_id": "test-session-456",
            "text_input": "I need help with this math problem",
            "speech_transcript": "Can you help me solve x plus two equals five?",
            "canvas_analysis": {
                "text_content": ["x + 2 = 5"],
                "mathematical_equations": ["x + 2 = 5"],
                "diagrams": [],
                "handwriting_text": "solve for x",
                "confidence_scores": {"text_detection": 0.9, "equation_recognition": 0.95},
                "raw_analysis": "Student wrote equation x + 2 = 5"
            },
            "uploaded_documents": ["algebra_worksheet.pdf"],
            "subject": "mathematics",
            "learning_level": "intermediate"
        }
    
    @pytest.fixture
    def mock_ai_response(self):
        """Mock AI response"""
        return AIResponse(
            text_response="Great question! What do you think we need to do to isolate x?",
            feedback_type=FeedbackType.QUESTION,
            confidence_score=0.92,
            whiteboard_actions=[
                {"action": "highlight", "target": "x + 2 = 5", "color": "yellow"}
            ],
            suggested_questions=["What operation undoes addition?", "What happens if we subtract 2 from both sides?"],
            learning_insights={
                "strengths": ["Correctly identified the equation", "Good problem setup"],
                "areas_for_improvement": ["Need to practice isolation steps"],
                "learning_objectives_met": ["equation_recognition"]
            },
            error_corrections=[],
            next_steps=["Practice isolating variables", "Try similar problems"]
        )
    
    def test_health_check_endpoint(self):
        """Test AI reasoning health check endpoint"""
        response = client.get("/api/ai/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
        assert "components" in data
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.ai_reasoning_engine.ai_reasoning_engine.process_multimodal_input')
    def test_process_multimodal_input_success(
        self, 
        mock_process, 
        mock_auth, 
        mock_user, 
        sample_multimodal_request, 
        mock_ai_response
    ):
        """Test successful multimodal input processing"""
        mock_auth.return_value = mock_user
        mock_process.return_value = mock_ai_response
        
        response = client.post("/api/ai/process", json=sample_multimodal_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["text_response"] == mock_ai_response.text_response
        assert data["feedback_type"] == mock_ai_response.feedback_type.value
        assert data["confidence_score"] == mock_ai_response.confidence_score
        assert data["session_id"] == sample_multimodal_request["session_id"]
        assert "timestamp" in data
        
        # Verify the AI engine was called with correct parameters
        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args.kwargs["session_id"] == sample_multimodal_request["session_id"]
        assert call_args.kwargs["user_id"] == mock_user["user_id"]
        assert call_args.kwargs["subject"] == SubjectArea.MATHEMATICS
        assert call_args.kwargs["learning_level"] == LearningLevel.INTERMEDIATE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
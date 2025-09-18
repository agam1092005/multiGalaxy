"""
Tests for TTS and Whiteboard API endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.services.text_to_speech import TTSResult, VoiceSettings, AudioFormat
from app.services.whiteboard_interaction import VisualDemonstration

# Create test client
client = TestClient(app)

class TestTTSWhiteboardAPI:
    """Test cases for TTS and Whiteboard API endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"Authorization": "Bearer test_token"}
    
    @pytest.fixture
    def mock_tts_result(self):
        """Mock TTS result for testing"""
        return TTSResult(
            audio_data=b"mock_audio_data",
            audio_format=AudioFormat.MP3,
            duration_seconds=5.0,
            text_length=20,
            voice_settings=VoiceSettings(),
            audio_url="data:audio/mpeg;base64,bW9ja19hdWRpb19kYXRh"
        )
    
    @pytest.fixture
    def mock_demonstration(self):
        """Mock visual demonstration for testing"""
        return VisualDemonstration(
            demonstration_id="test_demo_123",
            title="Test Demonstration",
            description="Test problem solving",
            actions=[],
            total_duration_ms=5000,
            synchronized_text=[],
            canvas_size=(800, 600)
        )
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.text_to_speech.text_to_speech_service.synthesize_speech')
    def test_synthesize_speech_endpoint(self, mock_synthesize, mock_auth, auth_headers, mock_tts_result):
        """Test TTS synthesis endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock TTS service
        mock_synthesize.return_value = mock_tts_result
        
        # Test request
        request_data = {
            "text": "Hello, this is a test.",
            "voice_gender": "female",
            "speaking_rate": 1.0,
            "pitch": 0.0,
            "audio_format": "mp3"
        }
        
        response = client.post(
            "/api/tts-whiteboard/synthesize",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "audio_url" in data
        assert "duration_seconds" in data
        assert "synthesis_id" in data
        assert data["text_length"] == 20
        assert data["audio_format"] == "mp3"
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.text_to_speech.text_to_speech_service.synthesize_educational_response')
    def test_educational_synthesis_endpoint(self, mock_synthesize, mock_auth, auth_headers, mock_tts_result):
        """Test educational TTS synthesis endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock TTS service
        mock_synthesize.return_value = mock_tts_result
        
        response = client.post(
            "/api/tts-whiteboard/educational-synthesis",
            params={
                "text_response": "Great job solving that equation!",
                "feedback_type": "encouragement",
                "session_id": "test_session"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "audio_url" in data
        assert "feedback_type" in data
        assert data["feedback_type"] == "encouragement"
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.whiteboard_interaction.whiteboard_interaction_service.create_visual_demonstration')
    def test_create_demonstration_endpoint(self, mock_create, mock_auth, auth_headers, mock_demonstration):
        """Test visual demonstration creation endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock whiteboard service
        mock_create.return_value = mock_demonstration
        
        request_data = {
            "problem_description": "Solve 2x + 3 = 7",
            "solution_steps": ["Subtract 3", "Divide by 2", "x = 2"],
            "subject_area": "mathematics",
            "canvas_width": 800,
            "canvas_height": 600
        }
        
        response = client.post(
            "/api/tts-whiteboard/create-demonstration",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["demonstration_id"] == "test_demo_123"
        assert data["title"] == "Test Demonstration"
        assert data["actions_count"] == 0
        assert data["canvas_size"] == [800, 600]
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.whiteboard_interaction.whiteboard_interaction_service.get_demonstration')
    @patch('app.services.whiteboard_interaction.whiteboard_interaction_service.convert_actions_to_frontend_format')
    def test_get_demonstration_actions_endpoint(self, mock_convert, mock_get, mock_auth, auth_headers, mock_demonstration):
        """Test get demonstration actions endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock whiteboard service
        mock_get.return_value = mock_demonstration
        mock_convert.return_value = []
        
        response = client.get(
            "/api/tts-whiteboard/demonstration/test_demo_123/actions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "actions" in data
        assert "total_actions" in data
        assert "estimated_duration_ms" in data
    
    @patch('app.core.auth.get_current_user')
    def test_get_demonstration_actions_not_found(self, mock_auth, auth_headers):
        """Test get demonstration actions when demonstration not found"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        with patch('app.services.whiteboard_interaction.whiteboard_interaction_service.get_demonstration') as mock_get:
            mock_get.return_value = None
            
            response = client.get(
                "/api/tts-whiteboard/demonstration/nonexistent/actions",
                headers=auth_headers
            )
            
            assert response.status_code == 404
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.whiteboard_interaction.whiteboard_interaction_service.create_error_correction_actions')
    @patch('app.services.whiteboard_interaction.whiteboard_interaction_service.convert_actions_to_frontend_format')
    def test_create_error_correction_endpoint(self, mock_convert, mock_create, mock_auth, auth_headers):
        """Test error correction creation endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock whiteboard service
        mock_create.return_value = []
        mock_convert.return_value = []
        
        request_data = {
            "error_location": [300, 200],
            "correction_text": "The answer should be 4, not 5",
            "canvas_width": 800,
            "canvas_height": 600
        }
        
        response = client.post(
            "/api/tts-whiteboard/error-correction",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "actions" in data
        assert "correction_id" in data
        assert "total_actions" in data
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.ai_reasoning_engine.ai_reasoning_engine.create_annotation_for_feedback')
    def test_create_annotation_endpoint(self, mock_create, mock_auth, auth_headers):
        """Test annotation creation endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock AI reasoning engine
        mock_create.return_value = {"id": "test_annotation", "type": "annotate"}
        
        request_data = {
            "text": "Good work on this step!",
            "position": [400, 300],
            "feedback_type": "encouragement"
        }
        
        response = client.post(
            "/api/tts-whiteboard/annotation",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "action" in data
        assert "annotation_id" in data
        assert data["feedback_type"] == "encouragement"
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.whiteboard_interaction.whiteboard_interaction_service.create_step_by_step_solution')
    def test_step_by_step_solution_endpoint(self, mock_create, mock_auth, auth_headers, mock_demonstration):
        """Test step-by-step solution creation endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock whiteboard service
        mock_create.return_value = mock_demonstration
        
        request_data = {
            "equation": "2x + 3 = 7",
            "solution_steps": [
                {"equation": "2x = 4", "explanation": "Subtract 3 from both sides"},
                {"equation": "x = 2", "explanation": "Divide both sides by 2"}
            ],
            "canvas_width": 800,
            "canvas_height": 600
        }
        
        response = client.post(
            "/api/tts-whiteboard/step-by-step-solution",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["demonstration_id"] == "test_demo_123"
        assert data["title"] == "Test Demonstration"
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.text_to_speech.text_to_speech_service.get_available_voices')
    def test_get_available_voices_endpoint(self, mock_get_voices, mock_auth, auth_headers):
        """Test get available voices endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock TTS service
        mock_voices = [
            {
                "name": "en-US-Journey-F",
                "language_codes": ["en-US"],
                "gender": "FEMALE",
                "natural_sample_rate": 24000
            }
        ]
        mock_get_voices.return_value = mock_voices
        
        response = client.get(
            "/api/tts-whiteboard/available-voices?language_code=en-US",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "voices" in data
        assert "language_code" in data
        assert "voice_presets" in data
        assert data["language_code"] == "en-US"
        assert len(data["voices"]) == 1
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.whiteboard_interaction.whiteboard_interaction_service.clear_demonstration')
    def test_clear_demonstration_endpoint(self, mock_clear, mock_auth, auth_headers):
        """Test clear demonstration endpoint"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        # Mock whiteboard service
        mock_clear.return_value = True
        
        response = client.delete(
            "/api/tts-whiteboard/demonstration/test_demo_123",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert data["demonstration_id"] == "test_demo_123"
    
    @patch('app.core.auth.get_current_user')
    def test_clear_demonstration_not_found(self, mock_auth, auth_headers):
        """Test clear demonstration when not found"""
        # Mock authentication
        mock_auth.return_value = {"user_id": "test_user"}
        
        with patch('app.services.whiteboard_interaction.whiteboard_interaction_service.clear_demonstration') as mock_clear:
            mock_clear.return_value = False
            
            response = client.delete(
                "/api/tts-whiteboard/demonstration/nonexistent",
                headers=auth_headers
            )
            
            assert response.status_code == 404
    
    @patch('app.services.text_to_speech.text_to_speech_service.validate_tts_setup')
    def test_health_check_endpoint(self, mock_validate):
        """Test health check endpoint"""
        # Mock TTS validation
        mock_validate.return_value = {
            "is_available": True,
            "client_initialized": True,
            "test_synthesis": True
        }
        
        response = client.get("/api/tts-whiteboard/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "tts_service" in data
        assert "whiteboard_service" in data
    
    def test_invalid_tts_request(self, auth_headers):
        """Test TTS synthesis with invalid request data"""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": "test_user"}
            
            # Empty text should fail validation
            request_data = {
                "text": "",
                "voice_gender": "female"
            }
            
            response = client.post(
                "/api/tts-whiteboard/synthesize",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 400
    
    def test_invalid_demonstration_request(self, auth_headers):
        """Test demonstration creation with invalid request data"""
        with patch('app.core.auth.get_current_user') as mock_auth:
            mock_auth.return_value = {"user_id": "test_user"}
            
            # Empty solution steps should fail validation
            request_data = {
                "problem_description": "Test problem",
                "solution_steps": [],
                "subject_area": "mathematics"
            }
            
            response = client.post(
                "/api/tts-whiteboard/create-demonstration",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 400

@pytest.mark.asyncio
async def test_tts_whiteboard_integration():
    """Integration test for TTS and whiteboard functionality"""
    # This would test the actual integration between services
    # For now, we'll test the basic workflow
    
    from app.services.text_to_speech import text_to_speech_service
    from app.services.whiteboard_interaction import whiteboard_interaction_service
    
    # Test TTS synthesis
    tts_result = await text_to_speech_service.synthesize_speech(
        text="Let's solve this equation step by step.",
        preset="tutor_female"
    )
    assert tts_result.text_length > 0
    
    # Test demonstration creation
    demonstration = await whiteboard_interaction_service.create_visual_demonstration(
        problem_description="Solve x + 5 = 10",
        solution_steps=["Subtract 5 from both sides", "x = 5"],
        subject_area="mathematics"
    )
    assert len(demonstration.actions) > 0
    
    # Test frontend format conversion
    frontend_actions = whiteboard_interaction_service.convert_actions_to_frontend_format(
        demonstration.actions
    )
    assert len(frontend_actions) == len(demonstration.actions)
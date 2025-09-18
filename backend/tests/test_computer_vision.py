"""
Tests for Computer Vision Service

Tests the computer vision functionality including canvas analysis,
equation recognition, handwriting recognition, and diagram analysis.
"""

import pytest
import asyncio
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

from app.services.computer_vision import (
    ComputerVisionService,
    CanvasAnalysisResult,
    DetectedObject,
    BoundingBox
)
from app.api.computer_vision import router
from app.models.user import User
from main import app

# Test client
client = TestClient(app)

class TestComputerVisionService:
    """Test cases for ComputerVisionService"""

    @pytest.fixture
    def cv_service(self):
        """Create a computer vision service instance for testing"""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-api-key'}):
            return ComputerVisionService()

    @pytest.fixture
    def sample_image_bytes(self):
        """Create a sample image for testing"""
        # Create a simple test image with text and shapes
        image = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(image)
        
        # Draw some text
        draw.text((50, 50), "Hello World", fill='black')
        draw.text((50, 100), "x + 2 = 5", fill='blue')
        
        # Draw some shapes
        draw.rectangle([200, 50, 300, 150], outline='red', width=2)
        draw.ellipse([250, 200, 350, 250], outline='green', width=2)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()

    @pytest.fixture
    def sample_canvas_data(self, sample_image_bytes):
        """Create sample canvas data (base64 encoded)"""
        encoded = base64.b64encode(sample_image_bytes).decode('utf-8')
        return f"data:image/png;base64,{encoded}"

    def test_extract_canvas_content(self, cv_service, sample_canvas_data):
        """Test canvas content extraction"""
        result = asyncio.run(cv_service.extract_canvas_content(sample_canvas_data))
        assert isinstance(result, bytes)
        assert len(result) > 0

    @patch('google.generativeai.GenerativeModel')
    def test_analyze_canvas_image(self, mock_model, cv_service, sample_image_bytes):
        """Test canvas image analysis"""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = '''
        {
            "text_content": ["Hello World", "Sample text"],
            "mathematical_equations": ["x + 2 = 5"],
            "diagrams": [{"type": "rectangle", "description": "Red rectangle", "elements": ["border"]}],
            "handwriting_text": "Handwritten note",
            "confidence_scores": {
                "text_detection": 0.95,
                "equation_recognition": 0.90,
                "diagram_analysis": 0.85,
                "handwriting_recognition": 0.88
            }
        }
        '''
        
        mock_vision_model = Mock()
        mock_vision_model.generate_content = AsyncMock(return_value=mock_response)
        mock_model.return_value = mock_vision_model
        
        cv_service.vision_model = mock_vision_model
        
        result = asyncio.run(cv_service.analyze_canvas_image(sample_image_bytes))
        
        assert isinstance(result, CanvasAnalysisResult)
        assert len(result.text_content) == 2
        assert len(result.mathematical_equations) == 1
        assert len(result.diagrams) == 1
        assert result.handwriting_text == "Handwritten note"
        assert result.confidence_scores['text_detection'] == 0.95

    @patch('google.generativeai.GenerativeModel')
    def test_recognize_mathematical_equations(self, mock_model, cv_service, sample_image_bytes):
        """Test mathematical equation recognition"""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "x + 2 = 5\n\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}\n\\int x \\, dx"
        
        mock_vision_model = Mock()
        mock_vision_model.generate_content = AsyncMock(return_value=mock_response)
        mock_model.return_value = mock_vision_model
        
        cv_service.vision_model = mock_vision_model
        
        result = asyncio.run(cv_service.recognize_mathematical_equations(sample_image_bytes))
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert "x + 2 = 5" in result
        assert "\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}" in result

    @patch('google.generativeai.GenerativeModel')
    def test_recognize_handwriting(self, mock_model, cv_service, sample_image_bytes):
        """Test handwriting recognition"""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "This is handwritten text that has been converted."
        
        mock_vision_model = Mock()
        mock_vision_model.generate_content = AsyncMock(return_value=mock_response)
        mock_model.return_value = mock_vision_model
        
        cv_service.vision_model = mock_vision_model
        
        result = asyncio.run(cv_service.recognize_handwriting(sample_image_bytes))
        
        assert isinstance(result, str)
        assert result == "This is handwritten text that has been converted."

    @patch('google.generativeai.GenerativeModel')
    def test_analyze_diagrams(self, mock_model, cv_service, sample_image_bytes):
        """Test diagram analysis"""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = '''
        [
            {
                "type": "geometric_shape",
                "description": "Rectangle with red border",
                "elements": ["rectangle", "border"],
                "educational_concept": "geometry",
                "complexity": "simple"
            }
        ]
        '''
        
        mock_vision_model = Mock()
        mock_vision_model.generate_content = AsyncMock(return_value=mock_response)
        mock_model.return_value = mock_vision_model
        
        cv_service.vision_model = mock_vision_model
        
        result = asyncio.run(cv_service.analyze_diagrams(sample_image_bytes))
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['type'] == 'geometric_shape'
        assert result[0]['complexity'] == 'simple'

    def test_detect_objects_with_bounding_boxes(self, cv_service, sample_image_bytes):
        """Test object detection with bounding boxes"""
        # This test uses the simplified implementation
        with patch.object(cv_service, 'analyze_canvas_image') as mock_analyze:
            mock_result = CanvasAnalysisResult(
                text_content=["Hello World"],
                mathematical_equations=["x + 2 = 5"],
                diagrams=[{"type": "rectangle", "description": "Test rectangle"}],
                handwriting_text="Test handwriting",
                confidence_scores={
                    "text_detection": 0.9,
                    "equation_recognition": 0.85
                },
                raw_analysis="Test analysis"
            )
            mock_analyze.return_value = mock_result
            
            result = asyncio.run(cv_service.detect_objects_with_bounding_boxes(sample_image_bytes))
            
            assert isinstance(result, list)
            assert len(result) >= 2  # At least text and equation objects
            
            # Check first object (text)
            text_obj = result[0]
            assert text_obj.type == 'text'
            assert text_obj.content == "Hello World"
            assert isinstance(text_obj.bounding_box, BoundingBox)

    def test_parse_text_analysis_fallback(self, cv_service):
        """Test fallback text parsing when JSON parsing fails"""
        test_text = """
        Text Content:
        - Hello World
        - Sample text
        
        Mathematical Equations:
        - x + 2 = 5
        - y = mx + b
        
        Handwriting:
        This is handwritten text
        """
        
        result = cv_service._parse_text_analysis(test_text)
        
        assert isinstance(result, dict)
        assert 'text_content' in result
        assert 'mathematical_equations' in result
        assert 'handwriting_text' in result
        assert 'confidence_scores' in result

class TestComputerVisionAPI:
    """Test cases for Computer Vision API endpoints"""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for authentication"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers"""
        return {"Authorization": "Bearer test-token"}

    def test_analyze_canvas_endpoint(self, mock_user, auth_headers):
        """Test canvas analysis endpoint"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            with patch('app.api.computer_vision.computer_vision_service') as mock_service:
                # Mock service response
                mock_result = CanvasAnalysisResult(
                    text_content=["Hello World"],
                    mathematical_equations=["x + 2 = 5"],
                    diagrams=[],
                    handwriting_text="",
                    confidence_scores={"text_detection": 0.9},
                    raw_analysis="Test"
                )
                mock_service.process_canvas_update = AsyncMock(return_value=mock_result)
                
                response = client.post(
                    "/api/computer-vision/analyze-canvas",
                    json={
                        "canvas_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                        "session_id": "test-session",
                        "subject": "math"
                    },
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "text_content" in data
                assert "mathematical_equations" in data
                assert "processing_time_ms" in data

    def test_recognize_equations_endpoint(self, mock_user, auth_headers):
        """Test equation recognition endpoint"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            with patch('app.api.computer_vision.computer_vision_service') as mock_service:
                mock_service.recognize_mathematical_equations = AsyncMock(
                    return_value=["x + 2 = 5", "y = mx + b"]
                )
                
                response = client.post(
                    "/api/computer-vision/recognize-equations",
                    json={
                        "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                    },
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "equations" in data
                assert "count" in data
                assert data["count"] == 2

    def test_recognize_handwriting_endpoint(self, mock_user, auth_headers):
        """Test handwriting recognition endpoint"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            with patch('app.api.computer_vision.computer_vision_service') as mock_service:
                mock_service.recognize_handwriting = AsyncMock(
                    return_value="This is handwritten text"
                )
                
                response = client.post(
                    "/api/computer-vision/recognize-handwriting",
                    json={
                        "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                    },
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "text" in data
                assert "character_count" in data
                assert data["text"] == "This is handwritten text"

    def test_analyze_diagrams_endpoint(self, mock_user, auth_headers):
        """Test diagram analysis endpoint"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            with patch('app.api.computer_vision.computer_vision_service') as mock_service:
                mock_diagrams = [
                    {
                        "type": "rectangle",
                        "description": "Red rectangle",
                        "elements": ["border"],
                        "educational_concept": "geometry",
                        "complexity": "simple"
                    }
                ]
                mock_service.analyze_diagrams = AsyncMock(return_value=mock_diagrams)
                
                response = client.post(
                    "/api/computer-vision/analyze-diagrams",
                    json={
                        "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                    },
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "diagrams" in data
                assert "count" in data
                assert data["count"] == 1

    def test_detect_objects_endpoint(self, mock_user, auth_headers):
        """Test object detection endpoint"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            with patch('app.api.computer_vision.computer_vision_service') as mock_service:
                mock_objects = [
                    DetectedObject(
                        type='text',
                        content='Hello World',
                        bounding_box=BoundingBox(x=10, y=20, width=100, height=30, confidence=0.9),
                        confidence=0.9
                    )
                ]
                mock_service.detect_objects_with_bounding_boxes = AsyncMock(return_value=mock_objects)
                
                response = client.post(
                    "/api/computer-vision/detect-objects",
                    json={
                        "canvas_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                    },
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "objects" in data
                assert "total_objects" in data
                assert data["total_objects"] == 1

    def test_upload_image_endpoint(self, mock_user, auth_headers):
        """Test image upload endpoint"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            with patch('app.api.computer_vision.computer_vision_service') as mock_service:
                mock_result = CanvasAnalysisResult(
                    text_content=["Uploaded image text"],
                    mathematical_equations=[],
                    diagrams=[],
                    handwriting_text="",
                    confidence_scores={"text_detection": 0.8},
                    raw_analysis="Upload test"
                )
                mock_service.analyze_canvas_image = AsyncMock(return_value=mock_result)
                
                # Create a test image file
                test_image = Image.new('RGB', (100, 100), color='white')
                img_byte_arr = io.BytesIO()
                test_image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                response = client.post(
                    "/api/computer-vision/upload-image",
                    files={"file": ("test.png", img_byte_arr, "image/png")},
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "filename" in data
                assert "analysis" in data
                assert "processing_time_ms" in data

    def test_health_endpoint(self):
        """Test computer vision health endpoint"""
        with patch('app.api.computer_vision.computer_vision_service') as mock_service:
            mock_service.api_key = "test-key"
            
            response = client.get("/api/computer-vision/health")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "status" in data
            assert "service" in data
            assert data["service"] == "computer-vision"

    def test_invalid_image_data(self, mock_user, auth_headers):
        """Test handling of invalid image data"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/computer-vision/analyze-canvas",
                json={
                    "canvas_data": "invalid-image-data"
                },
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_canvas_data(self, mock_user, auth_headers):
        """Test handling of missing canvas data"""
        with patch('app.api.computer_vision.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/computer-vision/analyze-canvas",
                json={},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST

class TestComputerVisionIntegration:
    """Integration tests for computer vision functionality"""

    def test_end_to_end_canvas_analysis(self):
        """Test complete canvas analysis workflow"""
        # This would be an integration test that tests the complete flow
        # from canvas data extraction to analysis results
        pass

    def test_real_time_analysis_performance(self):
        """Test performance of real-time analysis"""
        # This would test the performance characteristics
        # of the computer vision analysis under load
        pass

    def test_multimodal_content_analysis(self):
        """Test analysis of complex multimodal content"""
        # This would test analysis of canvas content that contains
        # text, equations, diagrams, and handwriting together
        pass

if __name__ == "__main__":
    pytest.main([__file__])
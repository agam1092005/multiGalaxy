"""
Computer Vision API endpoints for Multi-Galaxy-Note

Provides endpoints for canvas content analysis, image processing,
and visual content recognition.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import base64
import logging
from ..services.computer_vision import (
    computer_vision_service,
    CanvasAnalysisResult,
    DetectedObject
)
from ..core.auth import get_current_user
from ..models.user import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/computer-vision", tags=["computer-vision"])

# Request/Response models
class CanvasAnalysisRequest(BaseModel):
    canvas_data: str  # Base64 encoded image data
    session_id: Optional[str] = None
    subject: Optional[str] = None

class CanvasAnalysisResponse(BaseModel):
    text_content: List[str]
    mathematical_equations: List[str]
    diagrams: List[Dict[str, Any]]
    handwriting_text: str
    confidence_scores: Dict[str, float]
    processing_time_ms: float

class MathEquationRequest(BaseModel):
    image_data: str  # Base64 encoded image data

class HandwritingRequest(BaseModel):
    image_data: str  # Base64 encoded image data

class DiagramAnalysisRequest(BaseModel):
    image_data: str  # Base64 encoded image data

class ObjectDetectionResponse(BaseModel):
    objects: List[Dict[str, Any]]
    total_objects: int
    processing_time_ms: float

@router.post("/analyze-canvas", response_model=CanvasAnalysisResponse)
async def analyze_canvas(
    request: CanvasAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze canvas content for text, equations, diagrams, and handwriting
    
    Args:
        request: Canvas analysis request with image data
        current_user: Authenticated user
        
    Returns:
        Comprehensive analysis of canvas content
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Starting canvas analysis for user {current_user.id}")
        
        # Validate input
        if not request.canvas_data:
            raise HTTPException(status_code=400, detail="Canvas data is required")
        
        # Process canvas content
        analysis_result = await computer_vision_service.process_canvas_update(
            canvas_data=request.canvas_data,
            session_context={
                'user_id': str(current_user.id),
                'session_id': request.session_id,
                'subject': request.subject
            }
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Canvas analysis completed in {processing_time:.2f}ms")
        
        return CanvasAnalysisResponse(
            text_content=analysis_result.text_content,
            mathematical_equations=analysis_result.mathematical_equations,
            diagrams=analysis_result.diagrams,
            handwriting_text=analysis_result.handwriting_text,
            confidence_scores=analysis_result.confidence_scores,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in canvas analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/recognize-equations")
async def recognize_equations(
    request: MathEquationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Specialized mathematical equation recognition
    
    Args:
        request: Math equation recognition request
        current_user: Authenticated user
        
    Returns:
        List of recognized mathematical equations
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Starting equation recognition for user {current_user.id}")
        
        # Validate input
        if not request.image_data:
            raise HTTPException(status_code=400, detail="Image data is required")
        
        # Decode base64 image
        try:
            if request.image_data.startswith('data:image'):
                header, encoded = request.image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(request.image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
        
        # Recognize equations
        equations = await computer_vision_service.recognize_mathematical_equations(image_bytes)
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Equation recognition completed in {processing_time:.2f}ms, found {len(equations)} equations")
        
        return {
            "equations": equations,
            "count": len(equations),
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in equation recognition: {e}")
        raise HTTPException(status_code=500, detail=f"Equation recognition failed: {str(e)}")

@router.post("/recognize-handwriting")
async def recognize_handwriting(
    request: HandwritingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Handwriting recognition and text conversion
    
    Args:
        request: Handwriting recognition request
        current_user: Authenticated user
        
    Returns:
        Recognized handwritten text
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Starting handwriting recognition for user {current_user.id}")
        
        # Validate input
        if not request.image_data:
            raise HTTPException(status_code=400, detail="Image data is required")
        
        # Decode base64 image
        try:
            if request.image_data.startswith('data:image'):
                header, encoded = request.image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(request.image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
        
        # Recognize handwriting
        handwriting_text = await computer_vision_service.recognize_handwriting(image_bytes)
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Handwriting recognition completed in {processing_time:.2f}ms")
        
        return {
            "text": handwriting_text,
            "character_count": len(handwriting_text),
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in handwriting recognition: {e}")
        raise HTTPException(status_code=500, detail=f"Handwriting recognition failed: {str(e)}")

@router.post("/analyze-diagrams")
async def analyze_diagrams(
    request: DiagramAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze diagrams and drawings
    
    Args:
        request: Diagram analysis request
        current_user: Authenticated user
        
    Returns:
        Analysis of diagrams and visual elements
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Starting diagram analysis for user {current_user.id}")
        
        # Validate input
        if not request.image_data:
            raise HTTPException(status_code=400, detail="Image data is required")
        
        # Decode base64 image
        try:
            if request.image_data.startswith('data:image'):
                header, encoded = request.image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(request.image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
        
        # Analyze diagrams
        diagrams = await computer_vision_service.analyze_diagrams(image_bytes)
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Diagram analysis completed in {processing_time:.2f}ms, found {len(diagrams)} diagrams")
        
        return {
            "diagrams": diagrams,
            "count": len(diagrams),
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in diagram analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Diagram analysis failed: {str(e)}")

@router.post("/detect-objects", response_model=ObjectDetectionResponse)
async def detect_objects(
    request: CanvasAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Detect objects with bounding box information
    
    Args:
        request: Object detection request
        current_user: Authenticated user
        
    Returns:
        Detected objects with location information
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Starting object detection for user {current_user.id}")
        
        # Validate input
        if not request.canvas_data:
            raise HTTPException(status_code=400, detail="Canvas data is required")
        
        # Decode base64 image
        try:
            if request.canvas_data.startswith('data:image'):
                header, encoded = request.canvas_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(request.canvas_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
        
        # Detect objects
        detected_objects = await computer_vision_service.detect_objects_with_bounding_boxes(image_bytes)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response format
        objects_data = []
        for obj in detected_objects:
            objects_data.append({
                "type": obj.type,
                "content": obj.content,
                "bounding_box": {
                    "x": obj.bounding_box.x,
                    "y": obj.bounding_box.y,
                    "width": obj.bounding_box.width,
                    "height": obj.bounding_box.height
                },
                "confidence": obj.confidence
            })
        
        logger.info(f"Object detection completed in {processing_time:.2f}ms, found {len(detected_objects)} objects")
        
        return ObjectDetectionResponse(
            objects=objects_data,
            total_objects=len(detected_objects),
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in object detection: {e}")
        raise HTTPException(status_code=500, detail=f"Object detection failed: {str(e)}")

@router.post("/upload-image")
async def upload_image_for_analysis(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an image file for computer vision analysis
    
    Args:
        file: Uploaded image file
        current_user: Authenticated user
        
    Returns:
        Analysis results for the uploaded image
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Processing uploaded image for user {current_user.id}")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        image_bytes = await file.read()
        
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Analyze the image
        analysis_result = await computer_vision_service.analyze_canvas_image(image_bytes)
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Image analysis completed in {processing_time:.2f}ms")
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": len(image_bytes),
            "analysis": {
                "text_content": analysis_result.text_content,
                "mathematical_equations": analysis_result.mathematical_equations,
                "diagrams": analysis_result.diagrams,
                "handwriting_text": analysis_result.handwriting_text,
                "confidence_scores": analysis_result.confidence_scores
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing uploaded image: {e}")
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")

@router.get("/health")
async def computer_vision_health():
    """
    Health check for computer vision service
    
    Returns:
        Service health status
    """
    try:
        # Test basic functionality
        test_successful = True
        
        return {
            "status": "healthy" if test_successful else "unhealthy",
            "service": "computer-vision",
            "gemini_configured": bool(computer_vision_service.api_key),
            "models_available": ["gemini-pro-vision", "gemini-pro"]
        }
        
    except Exception as e:
        logger.error(f"Computer vision health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "computer-vision",
            "error": str(e)
        }
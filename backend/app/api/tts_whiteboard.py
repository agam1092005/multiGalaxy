"""
Text-to-Speech and Whiteboard Interaction API endpoints

Provides REST API endpoints for TTS synthesis and AI whiteboard interactions,
enabling synchronized voice and visual explanations.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
import uuid

from ..services.text_to_speech import (
    text_to_speech_service,
    VoiceSettings,
    VoiceGender,
    AudioFormat,
    TTSResult
)
from ..services.whiteboard_interaction import (
    whiteboard_interaction_service,
    VisualDemonstration,
    WhiteboardAction,
    DrawingAction,
    AnimationStyle
)
from ..services.ai_reasoning_engine import ai_reasoning_engine
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts-whiteboard", tags=["TTS & Whiteboard"])

# Request/Response Models

class TTSRequest(BaseModel):
    """Request model for text-to-speech synthesis"""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    voice_preset: Optional[str] = Field(None, description="Predefined voice preset")
    language_code: str = Field("en-US", description="Language code")
    voice_gender: VoiceGender = Field(VoiceGender.FEMALE, description="Voice gender")
    speaking_rate: float = Field(1.0, ge=0.25, le=4.0, description="Speaking rate")
    pitch: float = Field(0.0, ge=-20.0, le=20.0, description="Voice pitch")
    audio_format: AudioFormat = Field(AudioFormat.MP3, description="Audio format")
    
    @validator('text')
    def validate_text(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Text cannot be empty')
        return v.strip()

class TTSResponse(BaseModel):
    """Response model for TTS synthesis"""
    audio_url: str
    duration_seconds: Optional[float]
    text_length: int
    audio_format: str
    voice_settings: Dict[str, Any]
    synthesis_id: str
    created_at: datetime

class VisualDemonstrationRequest(BaseModel):
    """Request model for creating visual demonstrations"""
    problem_description: str = Field(..., min_length=1, description="Problem to demonstrate")
    solution_steps: List[str] = Field(..., min_items=1, description="Solution steps")
    subject_area: str = Field("mathematics", description="Academic subject")
    canvas_width: int = Field(800, ge=400, le=1200, description="Canvas width")
    canvas_height: int = Field(600, ge=300, le=900, description="Canvas height")
    
    @validator('solution_steps')
    def validate_steps(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one solution step is required')
        return [step.strip() for step in v if step.strip()]

class WhiteboardActionRequest(BaseModel):
    """Request model for individual whiteboard actions"""
    action_type: DrawingAction
    coordinates: List[float] = Field(..., min_items=2, description="Action coordinates")
    text: Optional[str] = Field(None, description="Text for text actions")
    color: str = Field("#000000", description="Drawing color")
    stroke_width: int = Field(2, ge=1, le=20, description="Stroke width")
    animation_style: AnimationStyle = Field(AnimationStyle.SMOOTH, description="Animation style")
    duration_ms: int = Field(1000, ge=100, le=10000, description="Animation duration")

class VisualDemonstrationResponse(BaseModel):
    """Response model for visual demonstrations"""
    demonstration_id: str
    title: str
    description: str
    total_duration_ms: int
    actions_count: int
    synchronized_text: List[Dict[str, Any]]
    canvas_size: Tuple[int, int]
    created_at: datetime

class WhiteboardActionsResponse(BaseModel):
    """Response model for whiteboard actions"""
    actions: List[Dict[str, Any]]
    total_actions: int
    estimated_duration_ms: int

class ErrorCorrectionRequest(BaseModel):
    """Request model for error correction visualization"""
    error_location: Tuple[float, float] = Field(..., description="Error position on canvas")
    correction_text: str = Field(..., min_length=1, description="Correction explanation")
    canvas_width: int = Field(800, description="Canvas width")
    canvas_height: int = Field(600, description="Canvas height")

class AnnotationRequest(BaseModel):
    """Request model for AI feedback annotations"""
    text: str = Field(..., min_length=1, description="Annotation text")
    position: Tuple[float, float] = Field(..., description="Annotation position")
    feedback_type: str = Field("explanation", description="Type of feedback")
    color: Optional[str] = Field(None, description="Annotation color")

# API Endpoints

@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Synthesize text to speech using Google TTS API
    
    Converts text to natural speech with customizable voice settings
    for educational AI responses.
    """
    try:
        # Create voice settings
        voice_settings = VoiceSettings(
            language_code=request.language_code,
            gender=request.voice_gender,
            speaking_rate=request.speaking_rate,
            pitch=request.pitch,
            audio_format=request.audio_format
        )
        
        # Generate cache key
        cache_key = f"tts_{hash(request.text)}_{request.voice_preset or 'custom'}"
        
        # Synthesize speech
        tts_result = await text_to_speech_service.synthesize_speech(
            text=request.text,
            voice_settings=voice_settings,
            preset=request.voice_preset,
            cache_key=cache_key
        )
        
        # Create audio URL if not already created
        if not tts_result.audio_url and tts_result.audio_data:
            tts_result.audio_url = text_to_speech_service.create_audio_url(
                tts_result.audio_data, tts_result.audio_format
            )
        
        synthesis_id = str(uuid.uuid4())
        
        return TTSResponse(
            audio_url=tts_result.audio_url or "",
            duration_seconds=tts_result.duration_seconds,
            text_length=tts_result.text_length,
            audio_format=tts_result.audio_format.value,
            voice_settings={
                "language_code": voice_settings.language_code,
                "gender": voice_settings.gender.value,
                "speaking_rate": voice_settings.speaking_rate,
                "pitch": voice_settings.pitch
            },
            synthesis_id=synthesis_id,
            created_at=datetime.utcnow()
        )
        
    except ValueError as e:
        logger.error(f"Validation error in TTS synthesis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while synthesizing speech"
        )

@router.post("/educational-synthesis")
async def synthesize_educational_response(
    text_response: str = Field(..., description="AI response text"),
    feedback_type: str = Field("explanation", description="Type of feedback"),
    session_id: Optional[str] = Field(None, description="Learning session ID"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Synthesize educational AI response with appropriate voice settings
    
    Uses predefined voice presets optimized for different types of
    educational feedback (encouragement, correction, explanation, etc.).
    """
    try:
        # Get session context for better voice selection
        context = None
        if session_id:
            context = await ai_reasoning_engine.get_session_context(session_id)
        
        # Synthesize educational response
        tts_result = await text_to_speech_service.synthesize_educational_response(
            text_response=text_response,
            feedback_type=feedback_type,
            context={
                "subject": context.subject.value if context else "general",
                "learning_level": context.learning_level.value if context else "intermediate",
                "session_id": session_id
            }
        )
        
        # Create audio URL
        if tts_result.audio_data:
            tts_result.audio_url = text_to_speech_service.create_audio_url(
                tts_result.audio_data, tts_result.audio_format
            )
        
        return {
            "audio_url": tts_result.audio_url or "",
            "duration_seconds": tts_result.duration_seconds,
            "feedback_type": feedback_type,
            "voice_preset_used": feedback_type,
            "synthesis_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error synthesizing educational response: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while synthesizing educational response"
        )

@router.post("/create-demonstration", response_model=VisualDemonstrationResponse)
async def create_visual_demonstration(
    request: VisualDemonstrationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a visual demonstration for step-by-step problem solving
    
    Generates synchronized whiteboard actions and text explanations
    for educational content visualization.
    """
    try:
        # Create visual demonstration
        demonstration = await whiteboard_interaction_service.create_visual_demonstration(
            problem_description=request.problem_description,
            solution_steps=request.solution_steps,
            subject_area=request.subject_area,
            canvas_size=(request.canvas_width, request.canvas_height)
        )
        
        return VisualDemonstrationResponse(
            demonstration_id=demonstration.demonstration_id,
            title=demonstration.title,
            description=demonstration.description,
            total_duration_ms=demonstration.total_duration_ms,
            actions_count=len(demonstration.actions),
            synchronized_text=demonstration.synchronized_text,
            canvas_size=demonstration.canvas_size,
            created_at=datetime.utcnow()
        )
        
    except ValueError as e:
        logger.error(f"Validation error creating demonstration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating visual demonstration: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating visual demonstration"
        )

@router.get("/demonstration/{demonstration_id}/actions", response_model=WhiteboardActionsResponse)
async def get_demonstration_actions(
    demonstration_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get whiteboard actions for a visual demonstration
    
    Returns the complete list of whiteboard actions in frontend-compatible format
    for rendering the visual demonstration.
    """
    try:
        # Get demonstration
        demonstration = await whiteboard_interaction_service.get_demonstration(demonstration_id)
        
        if not demonstration:
            raise HTTPException(
                status_code=404,
                detail=f"Demonstration {demonstration_id} not found"
            )
        
        # Convert actions to frontend format
        frontend_actions = whiteboard_interaction_service.convert_actions_to_frontend_format(
            demonstration.actions
        )
        
        return WhiteboardActionsResponse(
            actions=frontend_actions,
            total_actions=len(frontend_actions),
            estimated_duration_ms=demonstration.total_duration_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting demonstration actions: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving demonstration actions"
        )

@router.post("/error-correction")
async def create_error_correction(
    request: ErrorCorrectionRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create visual error correction on whiteboard
    
    Generates whiteboard actions to highlight errors and show corrections
    with appropriate visual indicators.
    """
    try:
        # Create error correction actions
        correction_actions = await whiteboard_interaction_service.create_error_correction_actions(
            error_location=request.error_location,
            correction_text=request.correction_text,
            canvas_size=(request.canvas_width, request.canvas_height)
        )
        
        # Convert to frontend format
        frontend_actions = whiteboard_interaction_service.convert_actions_to_frontend_format(
            correction_actions
        )
        
        return {
            "actions": frontend_actions,
            "correction_id": str(uuid.uuid4()),
            "total_actions": len(frontend_actions),
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating error correction: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating error correction"
        )

@router.post("/annotation")
async def create_annotation(
    request: AnnotationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create AI feedback annotation on whiteboard
    
    Generates annotation actions for AI feedback with appropriate
    styling based on feedback type.
    """
    try:
        # Map feedback type to enum
        from ..services.ai_reasoning_engine import FeedbackType
        feedback_type_map = {
            "encouragement": FeedbackType.ENCOURAGEMENT,
            "correction": FeedbackType.CORRECTION,
            "hint": FeedbackType.HINT,
            "explanation": FeedbackType.EXPLANATION,
            "question": FeedbackType.QUESTION,
            "validation": FeedbackType.VALIDATION
        }
        
        feedback_enum = feedback_type_map.get(request.feedback_type, FeedbackType.EXPLANATION)
        
        # Create annotation
        annotation_action = await ai_reasoning_engine.create_annotation_for_feedback(
            feedback_text=request.text,
            position=request.position,
            feedback_type=feedback_enum
        )
        
        return {
            "action": annotation_action,
            "annotation_id": str(uuid.uuid4()),
            "feedback_type": request.feedback_type,
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating annotation: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating annotation"
        )

@router.post("/step-by-step-solution", response_model=VisualDemonstrationResponse)
async def create_step_by_step_solution(
    equation: str = Field(..., description="Equation to solve"),
    solution_steps: List[Dict[str, Any]] = Field(..., description="Solution steps with equations and explanations"),
    canvas_width: int = Field(800, description="Canvas width"),
    canvas_height: int = Field(600, description="Canvas height"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create step-by-step solution visualization
    
    Generates a complete visual demonstration showing the step-by-step
    solution of an equation with synchronized explanations.
    """
    try:
        # Create step-by-step solution
        demonstration = await whiteboard_interaction_service.create_step_by_step_solution(
            equation=equation,
            solution_steps=solution_steps,
            canvas_size=(canvas_width, canvas_height)
        )
        
        return VisualDemonstrationResponse(
            demonstration_id=demonstration.demonstration_id,
            title=demonstration.title,
            description=demonstration.description,
            total_duration_ms=demonstration.total_duration_ms,
            actions_count=len(demonstration.actions),
            synchronized_text=demonstration.synchronized_text,
            canvas_size=demonstration.canvas_size,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error creating step-by-step solution: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating step-by-step solution"
        )

@router.get("/available-voices")
async def get_available_voices(
    language_code: str = "en-US",
    current_user: Dict = Depends(get_current_user)
):
    """
    Get available TTS voices for a language
    
    Returns list of available voices with their properties
    for voice selection in the frontend.
    """
    try:
        voices = await text_to_speech_service.get_available_voices(language_code)
        
        return {
            "language_code": language_code,
            "voices": voices,
            "total_voices": len(voices),
            "voice_presets": list(text_to_speech_service.voice_presets.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting available voices: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving available voices"
        )

@router.delete("/demonstration/{demonstration_id}")
async def clear_demonstration(
    demonstration_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Clear a stored visual demonstration
    
    Removes the demonstration from memory to free up resources.
    """
    try:
        cleared = await whiteboard_interaction_service.clear_demonstration(demonstration_id)
        
        if not cleared:
            raise HTTPException(
                status_code=404,
                detail=f"Demonstration {demonstration_id} not found"
            )
        
        return {
            "message": f"Demonstration {demonstration_id} cleared successfully",
            "demonstration_id": demonstration_id,
            "cleared_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing demonstration: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while clearing demonstration"
        )

@router.get("/health")
async def health_check():
    """
    Health check for TTS and whiteboard services
    
    Returns the status of TTS and whiteboard interaction services.
    """
    try:
        # Validate TTS setup
        tts_status = await text_to_speech_service.validate_tts_setup()
        
        # Get whiteboard service status
        whiteboard_status = {
            "service_initialized": True,
            "active_demonstrations": len(whiteboard_interaction_service.active_demonstrations),
            "drawing_templates": len(whiteboard_interaction_service.drawing_templates),
            "math_symbols": len(whiteboard_interaction_service.math_symbols)
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "tts_service": tts_status,
            "whiteboard_service": whiteboard_status
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
"""
AI Reasoning API endpoints for Multi-Galaxy-Note

Provides REST API endpoints for AI-powered educational interactions,
multimodal input processing, and conversation management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
import uuid

from ..services.ai_reasoning_engine import (
    ai_reasoning_engine,
    MultimodalInput,
    AIResponse,
    ConversationContext,
    FeedbackType,
    LearningLevel,
    SubjectArea
)
from ..services.computer_vision import CanvasAnalysisResult
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Reasoning"])

# Request/Response Models

class CanvasAnalysisRequest(BaseModel):
    """Request model for canvas analysis data"""
    text_content: List[str] = Field(default_factory=list)
    mathematical_equations: List[str] = Field(default_factory=list)
    diagrams: List[Dict[str, Any]] = Field(default_factory=list)
    handwriting_text: str = ""
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    raw_analysis: str = ""

class MultimodalInputRequest(BaseModel):
    """Request model for multimodal input"""
    session_id: str = Field(..., description="Learning session identifier")
    text_input: Optional[str] = Field(None, description="Text input from user")
    speech_transcript: Optional[str] = Field(None, description="Transcribed speech")
    canvas_analysis: Optional[CanvasAnalysisRequest] = Field(None, description="Canvas analysis results")
    uploaded_documents: List[str] = Field(default_factory=list, description="List of uploaded document IDs")
    subject: Optional[SubjectArea] = Field(None, description="Academic subject area")
    learning_level: Optional[LearningLevel] = Field(None, description="Student learning level")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Session ID cannot be empty')
        return v.strip()

class AIResponseModel(BaseModel):
    """Response model for AI-generated responses"""
    text_response: str
    feedback_type: FeedbackType
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    whiteboard_actions: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    learning_insights: Dict[str, Any] = Field(default_factory=dict)
    error_corrections: List[Dict[str, Any]] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    audio_url: Optional[str] = Field(None, description="TTS audio URL for response")
    audio_duration: Optional[float] = Field(None, description="Audio duration in seconds")
    visual_demonstration_id: Optional[str] = Field(None, description="Visual demonstration ID")
    synchronized_text: List[Dict[str, Any]] = Field(default_factory=list, description="Text synchronized with visual actions")
    session_id: str
    timestamp: datetime

class ConversationContextResponse(BaseModel):
    """Response model for conversation context"""
    session_id: str
    user_id: str
    subject: SubjectArea
    learning_level: LearningLevel
    current_topic: Optional[str]
    learning_objectives: List[str]
    conversation_length: int
    last_interaction: Optional[datetime]

class LearningAnalyticsResponse(BaseModel):
    """Response model for learning analytics"""
    user_id: str
    total_sessions: int
    subjects_studied: List[str]
    learning_objectives_met: List[str]
    common_feedback_types: Dict[str, int]
    average_confidence: float
    total_interactions: int
    generated_at: datetime

# API Endpoints

@router.post("/process", response_model=AIResponseModel)
async def process_multimodal_input(
    request: MultimodalInputRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Process multimodal input and generate AI educational response
    
    This endpoint handles combined text, speech, and visual inputs to provide
    intelligent educational feedback using the AI reasoning engine.
    """
    try:
        user_id = current_user.get("user_id", "anonymous")
        
        # Convert request to internal format
        canvas_analysis = None
        if request.canvas_analysis:
            canvas_analysis = CanvasAnalysisResult(
                text_content=request.canvas_analysis.text_content,
                mathematical_equations=request.canvas_analysis.mathematical_equations,
                diagrams=request.canvas_analysis.diagrams,
                handwriting_text=request.canvas_analysis.handwriting_text,
                confidence_scores=request.canvas_analysis.confidence_scores,
                raw_analysis=request.canvas_analysis.raw_analysis
            )
        
        multimodal_input = MultimodalInput(
            text_input=request.text_input,
            speech_transcript=request.speech_transcript,
            canvas_analysis=canvas_analysis,
            uploaded_documents=request.uploaded_documents,
            timestamp=datetime.utcnow()
        )
        
        # Process input through AI reasoning engine
        ai_response = await ai_reasoning_engine.process_multimodal_input(
            session_id=request.session_id,
            user_id=user_id,
            multimodal_input=multimodal_input,
            subject=request.subject,
            learning_level=request.learning_level
        )
        
        # Log interaction for analytics
        background_tasks.add_task(
            _log_interaction,
            user_id,
            request.session_id,
            multimodal_input,
            ai_response
        )
        
        # Convert to response model
        return AIResponseModel(
            text_response=ai_response.text_response,
            feedback_type=ai_response.feedback_type,
            confidence_score=ai_response.confidence_score,
            whiteboard_actions=ai_response.whiteboard_actions,
            suggested_questions=ai_response.suggested_questions,
            learning_insights=ai_response.learning_insights,
            error_corrections=ai_response.error_corrections,
            next_steps=ai_response.next_steps,
            audio_url=ai_response.audio_response.audio_url if ai_response.audio_response else None,
            audio_duration=ai_response.audio_response.duration_seconds if ai_response.audio_response else None,
            visual_demonstration_id=ai_response.visual_demonstration.demonstration_id if ai_response.visual_demonstration else None,
            synchronized_text=ai_response.visual_demonstration.synchronized_text if ai_response.visual_demonstration else [],
            session_id=request.session_id,
            timestamp=datetime.utcnow()
        )
        
    except ValueError as e:
        logger.error(f"Validation error in AI processing: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing multimodal input: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your input. Please try again."
        )

@router.get("/context/{session_id}", response_model=ConversationContextResponse)
async def get_conversation_context(
    session_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get conversation context for a learning session
    
    Returns the current state of the conversation including history,
    learning objectives, and session metadata.
    """
    try:
        user_id = current_user.get("user_id", "anonymous")
        
        context = await ai_reasoning_engine.get_session_context(session_id)
        
        if not context:
            raise HTTPException(
                status_code=404,
                detail=f"No conversation context found for session {session_id}"
            )
        
        # Verify user has access to this session
        if context.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this conversation session"
            )
        
        return ConversationContextResponse(
            session_id=context.session_id,
            user_id=context.user_id,
            subject=context.subject,
            learning_level=context.learning_level,
            current_topic=context.current_topic,
            learning_objectives=context.learning_objectives,
            conversation_length=len(context.conversation_history),
            last_interaction=context.last_interaction
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation context: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving conversation context"
        )

@router.delete("/context/{session_id}")
async def clear_conversation_context(
    session_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Clear conversation context for a learning session
    
    Removes all conversation history and resets the session state.
    """
    try:
        user_id = current_user.get("user_id", "anonymous")
        
        # Verify user has access to this session
        context = await ai_reasoning_engine.get_session_context(session_id)
        if context and context.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this conversation session"
            )
        
        cleared = await ai_reasoning_engine.clear_session_context(session_id)
        
        if not cleared:
            raise HTTPException(
                status_code=404,
                detail=f"No conversation context found for session {session_id}"
            )
        
        return {"message": f"Conversation context cleared for session {session_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing conversation context: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while clearing conversation context"
        )

@router.get("/analytics", response_model=LearningAnalyticsResponse)
async def get_learning_analytics(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get learning analytics for the current user
    
    Returns comprehensive analytics about learning progress,
    subjects studied, and interaction patterns.
    """
    try:
        user_id = current_user.get("user_id", "anonymous")
        
        analytics = await ai_reasoning_engine.get_learning_analytics(user_id)
        
        return LearningAnalyticsResponse(
            user_id=user_id,
            total_sessions=analytics['total_sessions'],
            subjects_studied=analytics['subjects_studied'],
            learning_objectives_met=analytics['learning_objectives_met'],
            common_feedback_types=analytics['common_feedback_types'],
            average_confidence=analytics['average_confidence'],
            total_interactions=analytics['total_interactions'],
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating learning analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating learning analytics"
        )

@router.post("/feedback")
async def submit_feedback(
    session_id: str,
    feedback_type: str,
    rating: int = Field(..., ge=1, le=5),
    comments: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Submit feedback about AI responses
    
    Allows users to rate and provide feedback on AI-generated responses
    to improve the system's performance.
    """
    try:
        user_id = current_user.get("user_id", "anonymous")
        
        # Validate feedback type
        valid_feedback_types = ["helpful", "accurate", "appropriate", "engaging"]
        if feedback_type not in valid_feedback_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid feedback type. Must be one of: {valid_feedback_types}"
            )
        
        # Store feedback (in a real implementation, this would go to a database)
        feedback_data = {
            "session_id": session_id,
            "user_id": user_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "comments": comments,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Received feedback: {feedback_data}")
        
        return {
            "message": "Feedback submitted successfully",
            "feedback_id": str(uuid.uuid4())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while submitting feedback"
        )

@router.get("/health")
async def health_check():
    """
    Health check endpoint for AI reasoning service
    
    Returns the current status of the AI reasoning engine and its dependencies.
    """
    try:
        # Check AI reasoning engine status
        engine_status = {
            "ai_reasoning_engine": "operational",
            "active_contexts": len(ai_reasoning_engine.active_contexts),
            "rag_system": "operational",
            "computer_vision": "operational",
            "audio_processor": "operational"
        }
        
        # Validate audio processor setup
        audio_validation = await ai_reasoning_engine.audio_processor.validate_audio_setup()
        engine_status["audio_processor_ready"] = audio_validation.get("is_ready", False)
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": engine_status
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# Helper Functions

async def _log_interaction(
    user_id: str,
    session_id: str,
    multimodal_input: MultimodalInput,
    ai_response: AIResponse
):
    """
    Log interaction for analytics and monitoring
    
    This is a background task that logs user interactions for
    analytics, monitoring, and system improvement.
    """
    try:
        interaction_log = {
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "input_modalities": {
                "text": bool(multimodal_input.text_input),
                "speech": bool(multimodal_input.speech_transcript),
                "canvas": bool(multimodal_input.canvas_analysis),
                "documents": len(multimodal_input.uploaded_documents)
            },
            "ai_response": {
                "feedback_type": ai_response.feedback_type.value,
                "confidence_score": ai_response.confidence_score,
                "response_length": len(ai_response.text_response),
                "has_whiteboard_actions": len(ai_response.whiteboard_actions) > 0,
                "has_error_corrections": len(ai_response.error_corrections) > 0
            }
        }
        
        # In a real implementation, this would be stored in a database
        logger.info(f"Interaction logged: {interaction_log}")
        
    except Exception as e:
        logger.error(f"Error logging interaction: {e}")
        # Don't raise exception as this is a background task
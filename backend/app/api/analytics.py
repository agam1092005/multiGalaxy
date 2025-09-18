"""
Analytics API endpoints for learning progress tracking and reporting.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.analytics import (
    LearningAnalyticsResponse, ProgressReportResponse, 
    RecommendationResponse, InteractionType
)
from app.models.user import User
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
analytics_service = AnalyticsService()


@router.get("/user/{user_id}", response_model=LearningAnalyticsResponse)
async def get_user_analytics(
    user_id: UUID,
    subject: Optional[str] = Query(None, description="Filter by subject"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics for a user
    
    Args:
        user_id: User ID to get analytics for
        subject: Optional subject filter
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User's learning analytics data
        
    Raises:
        HTTPException: If user not found or access denied
    """
    # Check permissions - users can only access their own data or their children's data
    if current_user.id != user_id:
        # TODO: Add parent-child relationship check
        # For now, only allow access to own data
        if current_user.role != "parent":
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only view your own analytics."
            )
    
    analytics = await analytics_service.get_user_analytics(db, user_id, subject)
    
    if not analytics:
        raise HTTPException(
            status_code=404,
            detail="No analytics data found for this user and subject"
        )
    
    return analytics


@router.get("/user/{user_id}/recommendations", response_model=List[RecommendationResponse])
async def get_user_recommendations(
    user_id: UUID,
    subject: Optional[str] = Query(None, description="Filter by subject"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized learning recommendations for a user
    
    Args:
        user_id: User ID to get recommendations for
        subject: Optional subject filter
        limit: Maximum number of recommendations to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of personalized recommendations
        
    Raises:
        HTTPException: If access denied
    """
    # Check permissions
    if current_user.id != user_id and current_user.role != "parent":
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only view your own recommendations."
        )
    
    recommendations = await analytics_service.generate_recommendations(
        db, user_id, subject, limit
    )
    
    return recommendations


@router.post("/user/{user_id}/interaction")
async def record_user_interaction(
    user_id: UUID,
    session_id: UUID,
    interaction_type: InteractionType,
    subject: str,
    skill_tags: List[str],
    success_rate: Optional[float] = None,
    time_spent: int = 0,
    difficulty_level: float = 0.5,
    interaction_data: Optional[dict] = None,
    ai_feedback_quality: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a new user interaction for analytics
    
    Args:
        user_id: User ID
        session_id: Learning session ID
        interaction_type: Type of interaction
        subject: Subject area
        skill_tags: List of relevant skills
        success_rate: Success rate (0.0 to 1.0)
        time_spent: Time spent in seconds
        difficulty_level: Difficulty level (0.0 to 1.0)
        interaction_data: Additional context data
        ai_feedback_quality: Quality of AI feedback (0.0 to 1.0)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If validation fails or access denied
    """
    # Check permissions
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only record your own interactions."
        )
    
    # Validate input ranges
    if success_rate is not None and not (0.0 <= success_rate <= 1.0):
        raise HTTPException(
            status_code=400,
            detail="Success rate must be between 0.0 and 1.0"
        )
    
    if not (0.0 <= difficulty_level <= 1.0):
        raise HTTPException(
            status_code=400,
            detail="Difficulty level must be between 0.0 and 1.0"
        )
    
    if ai_feedback_quality is not None and not (0.0 <= ai_feedback_quality <= 1.0):
        raise HTTPException(
            status_code=400,
            detail="AI feedback quality must be between 0.0 and 1.0"
        )
    
    try:
        interaction = await analytics_service.record_interaction(
            db=db,
            session_id=session_id,
            interaction_type=interaction_type,
            subject=subject,
            skill_tags=skill_tags,
            success_rate=success_rate,
            time_spent=time_spent,
            difficulty_level=difficulty_level,
            interaction_data=interaction_data,
            ai_feedback_quality=ai_feedback_quality
        )
        
        return {
            "message": "Interaction recorded successfully",
            "interaction_id": interaction.id
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record interaction: {str(e)}"
        )


@router.get("/user/{user_id}/progress-report", response_model=ProgressReportResponse)
async def generate_progress_report(
    user_id: UUID,
    report_type: str = Query("weekly", regex="^(weekly|monthly|custom)$"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a comprehensive progress report for a user
    
    Args:
        user_id: User ID to generate report for
        report_type: Type of report (weekly, monthly, custom)
        subject: Optional subject filter
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Generated progress report
        
    Raises:
        HTTPException: If access denied or report generation fails
    """
    # Check permissions
    if current_user.id != user_id and current_user.role != "parent":
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only generate your own progress reports."
        )
    
    try:
        report = await analytics_service.generate_progress_report(
            db, user_id, report_type, subject
        )
        return report
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate progress report: {str(e)}"
        )


@router.get("/parent-dashboard")
async def get_parent_dashboard(
    child_user_ids: List[UUID] = Query(..., description="List of child user IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard data for parents
    
    Args:
        child_user_ids: List of child user IDs to include in dashboard
        current_user: Current authenticated user (must be parent)
        db: Database session
        
    Returns:
        Parent dashboard data
        
    Raises:
        HTTPException: If user is not a parent or access denied
    """
    if current_user.role != "parent":
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only parents can access the parent dashboard."
        )
    
    # TODO: Verify that the current user is actually the parent of the specified children
    # This would require a parent-child relationship table
    
    try:
        dashboard_data = await analytics_service.get_parent_dashboard_data(
            db, current_user.id, child_user_ids
        )
        return dashboard_data
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load parent dashboard: {str(e)}"
        )


@router.get("/user/{user_id}/skill-trends")
async def get_skill_trends(
    user_id: UUID,
    subject: str,
    skill_name: str,
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get skill progression trends over time
    
    Args:
        user_id: User ID
        subject: Subject area
        skill_name: Name of the skill to analyze
        days: Number of days to look back
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Skill trend data
        
    Raises:
        HTTPException: If access denied or data not found
    """
    # Check permissions
    if current_user.id != user_id and current_user.role != "parent":
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only view your own skill trends."
        )
    
    # TODO: Implement skill trend analysis
    # This would involve querying historical skill assessment data
    # and calculating progression over time
    
    return {
        "message": "Skill trends endpoint - implementation pending",
        "user_id": user_id,
        "subject": subject,
        "skill_name": skill_name,
        "days": days
    }


@router.get("/user/{user_id}/learning-insights")
async def get_learning_insights(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated learning insights and patterns
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Learning insights and patterns
        
    Raises:
        HTTPException: If access denied
    """
    # Check permissions
    if current_user.id != user_id and current_user.role != "parent":
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only view your own learning insights."
        )
    
    # Get user analytics
    analytics = await analytics_service.get_user_analytics(db, user_id)
    
    if not analytics:
        raise HTTPException(
            status_code=404,
            detail="No analytics data found for this user"
        )
    
    # Generate insights based on learning patterns
    insights = {
        "learning_style": "visual" if analytics.learning_patterns.interaction_preferences.get(
            InteractionType.DRAWING, 0
        ) > 0.3 else "analytical",
        "optimal_session_length": min(analytics.learning_patterns.attention_span, 45 * 60),  # Max 45 minutes
        "best_study_times": analytics.learning_patterns.preferred_learning_times,
        "consistency_score": min(analytics.learning_patterns.session_frequency / 5.0, 1.0),  # Target 5 sessions/week
        "challenge_readiness": analytics.progress_metrics.success_rate > 0.8,
        "areas_of_strength": [
            skill.skill_name for skill in analytics.skill_assessments
            if skill.proficiency >= 0.8
        ][:5],
        "growth_opportunities": [
            skill.skill_name for skill in analytics.skill_assessments
            if skill.proficiency < 0.6 and skill.trend == "improving"
        ][:3]
    }
    
    return insights
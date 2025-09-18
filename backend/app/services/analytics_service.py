"""
Analytics service for learning progress tracking and reporting.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.analytics import (
    LearningAnalytics, SkillAssessment, UserInteraction, ProgressReport,
    LearningAnalyticsResponse, ProgressMetrics, LearningPatterns,
    RecommendationResponse, ProgressReportResponse, InteractionType
)
from app.models.user import User
from app.services.skill_assessment import SkillAssessmentEngine, ProgressTracker


class AnalyticsService:
    """Service for managing learning analytics and progress tracking"""
    
    def __init__(self):
        self.skill_engine = SkillAssessmentEngine()
        self.progress_tracker = ProgressTracker()
    
    async def get_user_analytics(
        self,
        db: Session,
        user_id: UUID,
        subject: Optional[str] = None
    ) -> Optional[LearningAnalyticsResponse]:
        """
        Get comprehensive analytics for a user
        
        Args:
            db: Database session
            user_id: User ID
            subject: Optional subject filter
            
        Returns:
            LearningAnalyticsResponse or None if no data
        """
        # Get or create analytics record
        query = db.query(LearningAnalytics).filter(
            LearningAnalytics.user_id == user_id
        )
        
        if subject:
            query = query.filter(LearningAnalytics.subject == subject)
        
        analytics = query.first()
        
        if not analytics:
            # Create new analytics if none exist
            if subject:
                analytics = await self._create_analytics_for_subject(db, user_id, subject)
            else:
                return None
        
        # Get skill assessments
        skill_assessments = await self.skill_engine.assess_user_skills(
            db, user_id, analytics.subject
        )
        
        # Get progress metrics
        progress_metrics = await self.progress_tracker.calculate_progress_metrics(
            db, user_id, analytics.subject
        )
        
        # Get learning patterns
        learning_patterns = await self._analyze_learning_patterns(
            db, user_id, analytics.subject
        )
        
        return LearningAnalyticsResponse(
            user_id=user_id,
            subject=analytics.subject,
            skill_assessments=list(skill_assessments.values()),
            progress_metrics=ProgressMetrics(**progress_metrics),
            learning_patterns=learning_patterns,
            last_updated=analytics.updated_at
        )
    
    async def record_interaction(
        self,
        db: Session,
        session_id: UUID,
        interaction_type: InteractionType,
        subject: str,
        skill_tags: List[str],
        success_rate: Optional[float] = None,
        time_spent: int = 0,
        difficulty_level: float = 0.5,
        interaction_data: Optional[Dict] = None,
        ai_feedback_quality: Optional[float] = None
    ) -> UserInteraction:
        """
        Record a new user interaction for analytics
        
        Args:
            db: Database session
            session_id: Learning session ID
            interaction_type: Type of interaction
            subject: Subject area
            skill_tags: List of relevant skills
            success_rate: Success rate (0.0 to 1.0)
            time_spent: Time spent in seconds
            difficulty_level: Difficulty level (0.0 to 1.0)
            interaction_data: Additional context data
            ai_feedback_quality: Quality of AI feedback (0.0 to 1.0)
            
        Returns:
            Created UserInteraction object
        """
        interaction = UserInteraction(
            session_id=session_id,
            interaction_type=interaction_type.value,
            subject=subject,
            skill_tags=skill_tags,
            success_rate=success_rate,
            time_spent=time_spent,
            difficulty_level=difficulty_level,
            interaction_data=interaction_data or {},
            ai_feedback_quality=ai_feedback_quality
        )
        
        db.add(interaction)
        db.flush()
        
        # Update skill assessments
        from app.models.learning_session import LearningSession
        session = db.query(LearningSession).filter(
            LearningSession.id == session_id
        ).first()
        
        if session:
            await self.skill_engine.update_skill_assessment(
                db, session.user_id, interaction
            )
        
        db.commit()
        return interaction
    
    async def generate_recommendations(
        self,
        db: Session,
        user_id: UUID,
        subject: Optional[str] = None,
        limit: int = 5
    ) -> List[RecommendationResponse]:
        """
        Generate personalized learning recommendations
        
        Args:
            db: Database session
            user_id: User ID
            subject: Optional subject filter
            limit: Maximum number of recommendations
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Get user's skill assessments
        analytics = await self.get_user_analytics(db, user_id, subject)
        if not analytics:
            return []
        
        # Analyze weak skills
        weak_skills = [
            skill for skill in analytics.skill_assessments
            if skill.proficiency < 0.6
        ]
        
        # Recommend practice for weak skills
        for skill in weak_skills[:3]:
            recommendations.append(RecommendationResponse(
                type="skill_focus",
                title=f"Practice {skill.skill_name}",
                description=f"Your {skill.skill_name} skills need attention. "
                           f"Current level: {skill.level.value}",
                priority=1 if skill.proficiency < 0.4 else 2,
                estimated_time=20,
                skills_targeted=[skill.skill_name],
                created_at=datetime.utcnow()
            ))
        
        # Analyze learning patterns for suggestions
        patterns = analytics.learning_patterns
        
        # Recommend optimal study times
        if patterns.preferred_learning_times:
            peak_hour = max(patterns.preferred_learning_times)
            recommendations.append(RecommendationResponse(
                type="practice_suggestion",
                title="Optimize Study Time",
                description=f"You perform best around {peak_hour}:00. "
                           f"Try scheduling important topics during this time.",
                priority=3,
                estimated_time=0,
                skills_targeted=[],
                created_at=datetime.utcnow()
            ))
        
        # Recommend difficulty adjustments
        if analytics.progress_metrics.success_rate > 0.9:
            recommendations.append(RecommendationResponse(
                type="difficulty_adjustment",
                title="Challenge Yourself",
                description="You're doing great! Try more challenging problems "
                           "to accelerate your learning.",
                priority=4,
                estimated_time=15,
                skills_targeted=[],
                created_at=datetime.utcnow()
            ))
        elif analytics.progress_metrics.success_rate < 0.5:
            recommendations.append(RecommendationResponse(
                type="difficulty_adjustment",
                title="Build Foundation",
                description="Focus on easier problems to build confidence "
                           "and strengthen your foundation.",
                priority=2,
                estimated_time=25,
                skills_targeted=[],
                created_at=datetime.utcnow()
            ))
        
        return recommendations[:limit]
    
    async def generate_progress_report(
        self,
        db: Session,
        user_id: UUID,
        report_type: str = "weekly",
        subject: Optional[str] = None
    ) -> ProgressReportResponse:
        """
        Generate a comprehensive progress report
        
        Args:
            db: Database session
            user_id: User ID
            report_type: Type of report (weekly, monthly, custom)
            subject: Optional subject filter
            
        Returns:
            Generated progress report
        """
        # Determine report period
        if report_type == "weekly":
            period_days = 7
        elif report_type == "monthly":
            period_days = 30
        else:
            period_days = 7  # Default to weekly
        
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Get analytics data
        analytics = await self.get_user_analytics(db, user_id, subject)
        progress_metrics = await self.progress_tracker.calculate_progress_metrics(
            db, user_id, subject, period_days
        )
        
        # Generate summary data
        summary_data = {
            "period_type": report_type,
            "total_study_time": progress_metrics["total_time_spent"],
            "sessions_completed": progress_metrics["sessions_completed"],
            "success_rate": progress_metrics["success_rate"],
            "improvement_rate": progress_metrics["improvement_rate"],
            "streak_days": progress_metrics["streak_days"],
            "subjects_covered": len(progress_metrics["subjects_studied"]),
            "top_skills": [],
            "areas_for_improvement": []
        }
        
        if analytics:
            # Add top performing skills
            top_skills = sorted(
                analytics.skill_assessments,
                key=lambda x: x.proficiency,
                reverse=True
            )[:3]
            summary_data["top_skills"] = [
                {"skill": skill.skill_name, "level": skill.level.value}
                for skill in top_skills
            ]
            
            # Add areas needing improvement
            weak_skills = sorted(
                analytics.skill_assessments,
                key=lambda x: x.proficiency
            )[:3]
            summary_data["areas_for_improvement"] = [
                {"skill": skill.skill_name, "proficiency": skill.proficiency}
                for skill in weak_skills
            ]
        
        # Generate recommendations
        recommendations = await self.generate_recommendations(db, user_id, subject)
        
        # Create and save report
        report = ProgressReport(
            user_id=user_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            summary_data=summary_data,
            recommendations=[rec.dict() for rec in recommendations]
        )
        
        db.add(report)
        db.commit()
        
        return ProgressReportResponse(
            id=report.id,
            report_type=report.report_type,
            period_start=report.period_start,
            period_end=report.period_end,
            summary_data=report.summary_data,
            recommendations=recommendations,
            generated_at=report.generated_at
        )
    
    async def get_parent_dashboard_data(
        self,
        db: Session,
        parent_user_id: UUID,
        child_user_ids: List[UUID]
    ) -> Dict:
        """
        Get comprehensive dashboard data for parents
        
        Args:
            db: Database session
            parent_user_id: Parent's user ID
            child_user_ids: List of child user IDs
            
        Returns:
            Dashboard data dictionary
        """
        dashboard_data = {
            "children": [],
            "summary": {
                "total_study_time": 0,
                "total_sessions": 0,
                "average_success_rate": 0.0,
                "active_children": 0
            }
        }
        
        total_success_rates = []
        
        for child_id in child_user_ids:
            # Get child's analytics
            child_analytics = await self.get_user_analytics(db, child_id)
            child_progress = await self.progress_tracker.calculate_progress_metrics(
                db, child_id, period_days=7
            )
            
            # Get child user info
            child_user = db.query(User).filter(User.id == child_id).first()
            
            child_data = {
                "user_id": child_id,
                "name": child_user.email if child_user else "Unknown",  # Replace with actual name field
                "weekly_progress": child_progress,
                "current_streak": child_progress["streak_days"],
                "subjects_studied": child_progress["subjects_studied"],
                "recent_activity": await self._get_recent_activity(db, child_id),
                "alerts": await self._generate_parent_alerts(db, child_id)
            }
            
            if child_analytics:
                child_data["skill_summary"] = {
                    "total_skills": len(child_analytics.skill_assessments),
                    "mastered_skills": len([
                        s for s in child_analytics.skill_assessments 
                        if s.proficiency >= 0.9
                    ]),
                    "developing_skills": len([
                        s for s in child_analytics.skill_assessments 
                        if 0.4 <= s.proficiency < 0.9
                    ]),
                    "needs_attention": len([
                        s for s in child_analytics.skill_assessments 
                        if s.proficiency < 0.4
                    ])
                }
            
            dashboard_data["children"].append(child_data)
            
            # Update summary
            dashboard_data["summary"]["total_study_time"] += child_progress["total_time_spent"]
            dashboard_data["summary"]["total_sessions"] += child_progress["sessions_completed"]
            
            if child_progress["success_rate"] > 0:
                total_success_rates.append(child_progress["success_rate"])
            
            if child_progress["sessions_completed"] > 0:
                dashboard_data["summary"]["active_children"] += 1
        
        # Calculate average success rate
        if total_success_rates:
            dashboard_data["summary"]["average_success_rate"] = (
                sum(total_success_rates) / len(total_success_rates)
            )
        
        return dashboard_data
    
    async def _create_analytics_for_subject(
        self,
        db: Session,
        user_id: UUID,
        subject: str
    ) -> LearningAnalytics:
        """Create new analytics record for a subject"""
        analytics = LearningAnalytics(
            user_id=user_id,
            subject=subject
        )
        db.add(analytics)
        db.commit()
        return analytics
    
    async def _analyze_learning_patterns(
        self,
        db: Session,
        user_id: UUID,
        subject: str
    ) -> LearningPatterns:
        """Analyze learning patterns for a user"""
        # Get interactions from last 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        interactions = db.query(UserInteraction).join(
            UserInteraction.session
        ).filter(
            and_(
                UserInteraction.subject == subject,
                UserInteraction.timestamp >= cutoff_date,
                UserInteraction.session.has(user_id=user_id)
            )
        ).all()
        
        if not interactions:
            return LearningPatterns(
                preferred_learning_times=[],
                session_frequency=0.0,
                attention_span=0,
                difficulty_preference=0.5,
                interaction_preferences={},
                common_mistake_patterns=[]
            )
        
        # Analyze preferred learning times
        hour_counts = {}
        for interaction in interactions:
            hour = interaction.timestamp.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        preferred_times = sorted(hour_counts.keys(), key=lambda x: hour_counts[x], reverse=True)[:3]
        
        # Calculate session frequency (sessions per week)
        unique_sessions = len(set(i.session_id for i in interactions))
        session_frequency = unique_sessions / 4.3  # 30 days / 7 days per week
        
        # Calculate average attention span
        session_durations = {}
        for interaction in interactions:
            if interaction.session_id not in session_durations:
                session_durations[interaction.session_id] = 0
            session_durations[interaction.session_id] += interaction.time_spent
        
        attention_span = (
            sum(session_durations.values()) // len(session_durations)
            if session_durations else 0
        )
        
        # Analyze difficulty preference
        difficulty_levels = [i.difficulty_level for i in interactions]
        difficulty_preference = sum(difficulty_levels) / len(difficulty_levels) if difficulty_levels else 0.5
        
        # Analyze interaction type preferences
        interaction_counts = {}
        for interaction in interactions:
            interaction_type = InteractionType(interaction.interaction_type)
            interaction_counts[interaction_type] = interaction_counts.get(interaction_type, 0) + 1
        
        total_interactions = len(interactions)
        interaction_preferences = {
            interaction_type: count / total_interactions
            for interaction_type, count in interaction_counts.items()
        }
        
        return LearningPatterns(
            preferred_learning_times=preferred_times,
            session_frequency=session_frequency,
            attention_span=attention_span,
            difficulty_preference=difficulty_preference,
            interaction_preferences=interaction_preferences,
            common_mistake_patterns=[]  # TODO: Implement mistake pattern analysis
        )
    
    async def _get_recent_activity(
        self,
        db: Session,
        user_id: UUID,
        days: int = 7
    ) -> List[Dict]:
        """Get recent activity summary for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        interactions = db.query(UserInteraction).join(
            UserInteraction.session
        ).filter(
            and_(
                UserInteraction.timestamp >= cutoff_date,
                UserInteraction.session.has(user_id=user_id)
            )
        ).order_by(desc(UserInteraction.timestamp)).limit(10).all()
        
        return [
            {
                "date": interaction.timestamp.isoformat(),
                "subject": interaction.subject,
                "type": interaction.interaction_type,
                "success_rate": interaction.success_rate,
                "time_spent": interaction.time_spent
            }
            for interaction in interactions
        ]
    
    async def _generate_parent_alerts(
        self,
        db: Session,
        child_user_id: UUID
    ) -> List[Dict]:
        """Generate alerts for parents about their child's progress"""
        alerts = []
        
        # Get recent progress
        progress = await self.progress_tracker.calculate_progress_metrics(
            db, child_user_id, period_days=7
        )
        
        # Check for concerning patterns
        if progress["success_rate"] < 0.4 and progress["sessions_completed"] > 3:
            alerts.append({
                "type": "performance_concern",
                "message": "Success rate has been low this week",
                "severity": "medium",
                "created_at": datetime.utcnow().isoformat()
            })
        
        if progress["sessions_completed"] == 0:
            alerts.append({
                "type": "inactivity",
                "message": "No study sessions this week",
                "severity": "high",
                "created_at": datetime.utcnow().isoformat()
            })
        
        if progress["streak_days"] >= 7:
            alerts.append({
                "type": "achievement",
                "message": f"Great job! {progress['streak_days']} day learning streak!",
                "severity": "positive",
                "created_at": datetime.utcnow().isoformat()
            })
        
        return alerts
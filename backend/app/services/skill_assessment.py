"""
Skill assessment algorithms for analyzing user interactions and determining proficiency levels.
"""
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.analytics import (
    SkillAssessment, UserInteraction, LearningAnalytics,
    SkillLevel, TrendDirection, InteractionType
)
from app.models.user import User


class SkillAssessmentEngine:
    """Engine for assessing user skills based on interaction data"""
    
    def __init__(self):
        self.skill_weights = {
            InteractionType.PROBLEM_SOLVING: 1.0,
            InteractionType.QUESTION_ASKING: 0.3,
            InteractionType.DRAWING: 0.6,
            InteractionType.SPEECH_INPUT: 0.4,
            InteractionType.DOCUMENT_UPLOAD: 0.2,
            InteractionType.WHITEBOARD_INTERACTION: 0.5
        }
        
        # Minimum interactions needed for reliable assessment
        self.min_interactions_for_assessment = 5
        
        # Time decay factor for older interactions (per day)
        self.time_decay_factor = 0.95
    
    async def assess_user_skills(
        self, 
        db: Session, 
        user_id: UUID, 
        subject: str,
        lookback_days: int = 30
    ) -> Dict[str, SkillAssessment]:
        """
        Assess all skills for a user in a given subject
        
        Args:
            db: Database session
            user_id: User ID to assess
            subject: Subject area to assess
            lookback_days: Number of days to look back for interactions
            
        Returns:
            Dictionary mapping skill names to assessments
        """
        # Get recent interactions
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
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
            return {}
        
        # Group interactions by skill
        skill_interactions = self._group_interactions_by_skill(interactions)
        
        # Assess each skill
        assessments = {}
        for skill_name, skill_interactions_list in skill_interactions.items():
            assessment = await self._assess_single_skill(
                skill_name, skill_interactions_list, subject
            )
            if assessment:
                assessments[skill_name] = assessment
        
        return assessments
    
    def _group_interactions_by_skill(
        self, 
        interactions: List[UserInteraction]
    ) -> Dict[str, List[UserInteraction]]:
        """Group interactions by skill tags"""
        skill_groups = {}
        
        for interaction in interactions:
            for skill in interaction.skill_tags or []:
                if skill not in skill_groups:
                    skill_groups[skill] = []
                skill_groups[skill].append(interaction)
        
        return skill_groups
    
    async def _assess_single_skill(
        self,
        skill_name: str,
        interactions: List[UserInteraction],
        subject: str
    ) -> Optional[SkillAssessment]:
        """
        Assess proficiency for a single skill
        
        Args:
            skill_name: Name of the skill to assess
            interactions: List of interactions for this skill
            subject: Subject area
            
        Returns:
            SkillAssessment object or None if insufficient data
        """
        if len(interactions) < self.min_interactions_for_assessment:
            return None
        
        # Calculate weighted proficiency score
        proficiency = self._calculate_proficiency(interactions)
        
        # Calculate confidence based on data quality and quantity
        confidence = self._calculate_confidence(interactions)
        
        # Determine skill level
        level = self._determine_skill_level(proficiency)
        
        # Calculate trend
        trend = self._calculate_trend(interactions)
        
        return SkillAssessment(
            skill_name=skill_name,
            proficiency=proficiency,
            confidence=confidence,
            level=level.value,
            trend=trend.value,
            evidence_count=len(interactions),
            last_assessed=datetime.utcnow()
        )
    
    def _calculate_proficiency(self, interactions: List[UserInteraction]) -> float:
        """
        Calculate proficiency score based on weighted interactions
        
        Args:
            interactions: List of interactions for the skill
            
        Returns:
            Proficiency score between 0.0 and 1.0
        """
        total_weight = 0.0
        weighted_score = 0.0
        current_time = datetime.utcnow()
        
        for interaction in interactions:
            # Get base weight for interaction type
            base_weight = self.skill_weights.get(
                InteractionType(interaction.interaction_type), 0.5
            )
            
            # Apply time decay
            days_old = (current_time - interaction.timestamp).days
            time_weight = self.time_decay_factor ** days_old
            
            # Apply difficulty adjustment
            difficulty_weight = 0.5 + (interaction.difficulty_level * 0.5)
            
            # Calculate final weight
            final_weight = base_weight * time_weight * difficulty_weight
            
            # Use success rate as the score for this interaction
            interaction_score = interaction.success_rate or 0.0
            
            weighted_score += interaction_score * final_weight
            total_weight += final_weight
        
        if total_weight == 0:
            return 0.0
        
        return min(1.0, max(0.0, weighted_score / total_weight))
    
    def _calculate_confidence(self, interactions: List[UserInteraction]) -> float:
        """
        Calculate confidence in the assessment based on data quality
        
        Args:
            interactions: List of interactions for the skill
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence from number of interactions
        interaction_confidence = min(1.0, len(interactions) / 20.0)
        
        # Confidence from recency of data
        current_time = datetime.utcnow()
        recent_interactions = [
            i for i in interactions 
            if (current_time - i.timestamp).days <= 7
        ]
        recency_confidence = min(1.0, len(recent_interactions) / 5.0)
        
        # Confidence from consistency of results
        success_rates = [i.success_rate for i in interactions if i.success_rate is not None]
        if len(success_rates) > 1:
            variance = sum((x - sum(success_rates)/len(success_rates))**2 for x in success_rates) / len(success_rates)
            consistency_confidence = max(0.0, 1.0 - (variance * 2))
        else:
            consistency_confidence = 0.5
        
        # Weighted average of confidence factors
        return (
            interaction_confidence * 0.4 +
            recency_confidence * 0.3 +
            consistency_confidence * 0.3
        )
    
    def _determine_skill_level(self, proficiency: float) -> SkillLevel:
        """
        Determine skill level based on proficiency score
        
        Args:
            proficiency: Proficiency score between 0.0 and 1.0
            
        Returns:
            SkillLevel enum value
        """
        if proficiency >= 0.9:
            return SkillLevel.MASTERY
        elif proficiency >= 0.75:
            return SkillLevel.ADVANCED
        elif proficiency >= 0.6:
            return SkillLevel.PROFICIENT
        elif proficiency >= 0.4:
            return SkillLevel.DEVELOPING
        else:
            return SkillLevel.BEGINNER
    
    def _calculate_trend(self, interactions: List[UserInteraction]) -> TrendDirection:
        """
        Calculate learning trend based on recent performance
        
        Args:
            interactions: List of interactions for the skill
            
        Returns:
            TrendDirection enum value
        """
        if len(interactions) < 6:
            return TrendDirection.INSUFFICIENT_DATA
        
        # Sort by timestamp
        sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
        
        # Split into first and second half
        mid_point = len(sorted_interactions) // 2
        first_half = sorted_interactions[:mid_point]
        second_half = sorted_interactions[mid_point:]
        
        # Calculate average success rates
        first_avg = sum(i.success_rate or 0 for i in first_half) / len(first_half)
        second_avg = sum(i.success_rate or 0 for i in second_half) / len(second_half)
        
        # Determine trend
        improvement = second_avg - first_avg
        
        if improvement > 0.1:
            return TrendDirection.IMPROVING
        elif improvement < -0.1:
            return TrendDirection.DECLINING
        else:
            return TrendDirection.STABLE
    
    async def update_skill_assessment(
        self,
        db: Session,
        user_id: UUID,
        interaction: UserInteraction
    ) -> None:
        """
        Update skill assessments based on a new interaction
        
        Args:
            db: Database session
            user_id: User ID
            interaction: New interaction to process
        """
        if not interaction.skill_tags:
            return
        
        # Get or create analytics record
        analytics = db.query(LearningAnalytics).filter(
            and_(
                LearningAnalytics.user_id == user_id,
                LearningAnalytics.subject == interaction.subject
            )
        ).first()
        
        if not analytics:
            analytics = LearningAnalytics(
                user_id=user_id,
                subject=interaction.subject
            )
            db.add(analytics)
            db.flush()
        
        # Update assessments for each skill
        for skill_name in interaction.skill_tags:
            # Get recent interactions for this skill
            recent_interactions = db.query(UserInteraction).join(
                UserInteraction.session
            ).filter(
                and_(
                    UserInteraction.subject == interaction.subject,
                    UserInteraction.skill_tags.contains([skill_name]),
                    UserInteraction.timestamp >= datetime.utcnow() - timedelta(days=30),
                    UserInteraction.session.has(user_id=user_id)
                )
            ).all()
            
            # Assess the skill
            assessment = await self._assess_single_skill(
                skill_name, recent_interactions, interaction.subject
            )
            
            if assessment:
                # Update or create skill assessment record
                existing = db.query(SkillAssessment).filter(
                    and_(
                        SkillAssessment.analytics_id == analytics.id,
                        SkillAssessment.skill_name == skill_name
                    )
                ).first()
                
                if existing:
                    existing.proficiency = assessment.proficiency
                    existing.confidence = assessment.confidence
                    existing.level = assessment.level
                    existing.trend = assessment.trend
                    existing.evidence_count = assessment.evidence_count
                    existing.last_assessed = assessment.last_assessed
                else:
                    assessment.analytics_id = analytics.id
                    db.add(assessment)
        
        # Update analytics timestamp
        analytics.updated_at = datetime.utcnow()
        db.commit()


class ProgressTracker:
    """Tracks learning progress and generates metrics"""
    
    def __init__(self):
        self.skill_assessment_engine = SkillAssessmentEngine()
    
    async def calculate_progress_metrics(
        self,
        db: Session,
        user_id: UUID,
        subject: Optional[str] = None,
        period_days: int = 30
    ) -> Dict:
        """
        Calculate comprehensive progress metrics for a user
        
        Args:
            db: Database session
            user_id: User ID
            subject: Optional subject filter
            period_days: Period to calculate metrics for
            
        Returns:
            Dictionary containing progress metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Base query for interactions
        query = db.query(UserInteraction).join(
            UserInteraction.session
        ).filter(
            and_(
                UserInteraction.timestamp >= cutoff_date,
                UserInteraction.session.has(user_id=user_id)
            )
        )
        
        if subject:
            query = query.filter(UserInteraction.subject == subject)
        
        interactions = query.all()
        
        if not interactions:
            return self._empty_progress_metrics()
        
        # Calculate metrics
        total_time = sum(i.time_spent for i in interactions)
        sessions = len(set(i.session_id for i in interactions))
        problems_solved = len([i for i in interactions if i.interaction_type == InteractionType.PROBLEM_SOLVING])
        
        success_rates = [i.success_rate for i in interactions if i.success_rate is not None]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        
        avg_session_duration = total_time // sessions if sessions > 0 else 0
        
        # Calculate streak
        streak_days = await self._calculate_streak(db, user_id, subject)
        
        # Get subjects studied
        subjects_studied = list(set(i.subject for i in interactions))
        
        # Calculate improvement rate
        improvement_rate = await self._calculate_improvement_rate(db, user_id, subject, period_days)
        
        return {
            "total_time_spent": total_time,
            "sessions_completed": sessions,
            "problems_solved": problems_solved,
            "success_rate": avg_success_rate,
            "average_session_duration": avg_session_duration,
            "streak_days": streak_days,
            "subjects_studied": subjects_studied,
            "improvement_rate": improvement_rate
        }
    
    def _empty_progress_metrics(self) -> Dict:
        """Return empty progress metrics"""
        return {
            "total_time_spent": 0,
            "sessions_completed": 0,
            "problems_solved": 0,
            "success_rate": 0.0,
            "average_session_duration": 0,
            "streak_days": 0,
            "subjects_studied": [],
            "improvement_rate": 0.0
        }
    
    async def _calculate_streak(
        self,
        db: Session,
        user_id: UUID,
        subject: Optional[str]
    ) -> int:
        """Calculate current learning streak in days"""
        # Get sessions grouped by date
        query = db.query(
            func.date(UserInteraction.timestamp).label('date')
        ).join(
            UserInteraction.session
        ).filter(
            UserInteraction.session.has(user_id=user_id)
        )
        
        if subject:
            query = query.filter(UserInteraction.subject == subject)
        
        dates = query.distinct().order_by(
            func.date(UserInteraction.timestamp).desc()
        ).all()
        
        if not dates:
            return 0
        
        # Calculate consecutive days
        streak = 0
        current_date = datetime.utcnow().date()
        
        for date_row in dates:
            date = date_row.date
            if date == current_date or date == current_date - timedelta(days=streak):
                streak += 1
                current_date = date
            else:
                break
        
        return streak
    
    async def _calculate_improvement_rate(
        self,
        db: Session,
        user_id: UUID,
        subject: Optional[str],
        period_days: int
    ) -> float:
        """Calculate improvement rate over the period"""
        # Split period in half and compare
        mid_date = datetime.utcnow() - timedelta(days=period_days // 2)
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # First half interactions
        first_half_query = db.query(UserInteraction).join(
            UserInteraction.session
        ).filter(
            and_(
                UserInteraction.timestamp >= start_date,
                UserInteraction.timestamp < mid_date,
                UserInteraction.session.has(user_id=user_id)
            )
        )
        
        # Second half interactions
        second_half_query = db.query(UserInteraction).join(
            UserInteraction.session
        ).filter(
            and_(
                UserInteraction.timestamp >= mid_date,
                UserInteraction.session.has(user_id=user_id)
            )
        )
        
        if subject:
            first_half_query = first_half_query.filter(UserInteraction.subject == subject)
            second_half_query = second_half_query.filter(UserInteraction.subject == subject)
        
        first_half = first_half_query.all()
        second_half = second_half_query.all()
        
        if not first_half or not second_half:
            return 0.0
        
        # Calculate average success rates
        first_success = [i.success_rate for i in first_half if i.success_rate is not None]
        second_success = [i.success_rate for i in second_half if i.success_rate is not None]
        
        if not first_success or not second_success:
            return 0.0
        
        first_avg = sum(first_success) / len(first_success)
        second_avg = sum(second_success) / len(second_success)
        
        if first_avg == 0:
            return 0.0
        
        return ((second_avg - first_avg) / first_avg) * 100
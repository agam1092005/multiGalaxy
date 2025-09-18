"""
Comprehensive tests for AI Reasoning Engine

Tests cover AI response quality, appropriateness, multimodal processing,
context management, and pedagogical reasoning logic.
"""

import pytest
import asyncio
import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.services.ai_reasoning_engine import (
    AIReasoningEngine,
    ConversationContext,
    MultimodalInput,
    AIResponse,
    FeedbackType,
    LearningLevel,
    SubjectArea
)
from app.services.computer_vision import CanvasAnalysisResult


class TestAIReasoningEngine:
    """Test suite for AI Reasoning Engine"""
    
    @pytest.fixture
    def ai_engine(self):
        """Create AI reasoning engine instance for testing"""
        # Set testing environment
        os.environ["TESTING"] = "true"
        os.environ["GEMINI_API_KEY"] = "test-key"
        
        engine = AIReasoningEngine()
        return engine
    
    @pytest.fixture
    def sample_context(self):
        """Create sample conversation context"""
        return ConversationContext(
            session_id="test-session-123",
            user_id="test-user-456",
            subject=SubjectArea.MATHEMATICS,
            learning_level=LearningLevel.INTERMEDIATE,
            conversation_history=[],
            current_topic="algebra",
            learning_objectives=["solve_linear_equations", "understand_variables"]
        )
    
    @pytest.fixture
    def sample_multimodal_input(self):
        """Create sample multimodal input"""
        canvas_analysis = CanvasAnalysisResult(
            text_content=["x + 2 = 5"],
            mathematical_equations=["x + 2 = 5"],
            diagrams=[],
            handwriting_text="solve for x",
            confidence_scores={"text_detection": 0.9, "equation_recognition": 0.95},
            raw_analysis="Student wrote equation x + 2 = 5"
        )
        
        return MultimodalInput(
            text_input="I need help solving this equation",
            speech_transcript="Can you help me solve x plus two equals five?",
            canvas_analysis=canvas_analysis,
            uploaded_documents=["algebra_worksheet.pdf"]
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, ai_engine):
        """Test AI reasoning engine initialization"""
        assert ai_engine is not None
        assert ai_engine.api_key == "test-key"
        assert ai_engine.rag_system is not None
        assert ai_engine.computer_vision is not None
        assert ai_engine.audio_processor is not None
        assert len(ai_engine.pedagogical_prompts) == 3
        assert "socratic" in ai_engine.pedagogical_prompts
        assert "scaffolding" in ai_engine.pedagogical_prompts
        assert "constructivist" in ai_engine.pedagogical_prompts
    
    @pytest.mark.asyncio
    async def test_context_creation_and_management(self, ai_engine):
        """Test conversation context creation and management"""
        session_id = "test-session-001"
        user_id = "test-user-001"
        
        # Test context creation
        context = await ai_engine._get_or_create_context(
            session_id, user_id, SubjectArea.SCIENCE, LearningLevel.BEGINNER
        )
        
        assert context.session_id == session_id
        assert context.user_id == user_id
        assert context.subject == SubjectArea.SCIENCE
        assert context.learning_level == LearningLevel.BEGINNER
        assert context.last_interaction is not None
        assert session_id in ai_engine.active_contexts
        
        # Test context retrieval
        retrieved_context = await ai_engine._get_or_create_context(session_id, user_id)
        assert retrieved_context.session_id == session_id
        assert len(ai_engine.active_contexts) == 1  # Should not create duplicate
    
    @pytest.mark.asyncio
    async def test_multimodal_input_combination(self, ai_engine, sample_multimodal_input, sample_context):
        """Test combining inputs from multiple modalities"""
        combined_input = await ai_engine._combine_input_modalities(
            sample_multimodal_input, sample_context
        )
        
        assert "Text input: I need help solving this equation" in combined_input
        assert "Student said: Can you help me solve x plus two equals five?" in combined_input
        assert "Canvas content:" in combined_input
        assert "x + 2 = 5" in combined_input
        assert "Referenced documents: algebra_worksheet.pdf" in combined_input
    
    @pytest.mark.asyncio
    async def test_canvas_content_summarization(self, ai_engine):
        """Test canvas content summarization"""
        canvas_analysis = CanvasAnalysisResult(
            text_content=["Hello World", "Test Text"],
            mathematical_equations=["2x + 3 = 7", "y = mx + b"],
            diagrams=[{"description": "triangle diagram", "type": "geometry"}],
            handwriting_text="student notes",
            confidence_scores={},
            raw_analysis=""
        )
        
        summary = await ai_engine._summarize_canvas_content(canvas_analysis)
        
        assert "Text: Hello World, Test Text" in summary
        assert "Math equations: 2x + 3 = 7, y = mx + b" in summary
        assert "Handwritten: student notes" in summary
        assert "Diagrams: triangle diagram" in summary
    
    @pytest.mark.asyncio
    async def test_educational_prompt_building(self, ai_engine, sample_context):
        """Test educational prompt construction"""
        combined_input = "I'm solving x + 2 = 5"
        rag_context = {
            'relevant_content': 'Linear equations can be solved by isolating the variable.',
            'sources': [],
            'subjects_covered': ['mathematics'],
            'total_chunks': 1
        }
        
        prompt = ai_engine._build_educational_prompt(combined_input, rag_context, sample_context)
        
        assert "Socratic method" in prompt or "scaffolding" in prompt or "constructivist" in prompt
        assert "Subject: mathematics" in prompt
        assert "Learning Level: intermediate" in prompt
        assert "I'm solving x + 2 = 5" in prompt
        assert "Linear equations can be solved by isolating the variable." in prompt
        assert "RESPONSE FORMAT:" in prompt
        assert "JSON" in prompt
    
    @pytest.mark.asyncio
    async def test_ai_response_parsing(self, ai_engine, sample_context):
        """Test AI response parsing from JSON"""
        response_text = '''
        Here's my response:
        {
            "text_response": "Great question! What do you think we need to do to isolate x?",
            "feedback_type": "question",
            "confidence_score": 0.92,
            "whiteboard_actions": [
                {"action": "highlight", "target": "x + 2 = 5", "color": "yellow"}
            ],
            "suggested_questions": ["What operation undoes addition?", "What happens if we subtract 2 from both sides?"],
            "learning_insights": {
                "strengths": ["Correctly identified the equation", "Good problem setup"],
                "areas_for_improvement": ["Need to practice isolation steps"],
                "learning_objectives_met": ["equation_recognition"]
            },
            "error_corrections": [],
            "next_steps": ["Practice isolating variables", "Try similar problems"]
        }
        '''
        
        parsed_response = await ai_engine._parse_ai_response(response_text, sample_context)
        
        assert isinstance(parsed_response, AIResponse)
        assert parsed_response.text_response == "Great question! What do you think we need to do to isolate x?"
        assert parsed_response.feedback_type == FeedbackType.QUESTION
        assert parsed_response.confidence_score == 0.92
        assert len(parsed_response.whiteboard_actions) == 1
        assert len(parsed_response.suggested_questions) == 2
        assert "strengths" in parsed_response.learning_insights
        assert len(parsed_response.next_steps) == 2
    
    @pytest.mark.asyncio
    async def test_ai_response_parsing_fallback(self, ai_engine, sample_context):
        """Test AI response parsing fallback for malformed JSON"""
        response_text = "This is a plain text response without JSON formatting."
        
        parsed_response = await ai_engine._parse_ai_response(response_text, sample_context)
        
        assert isinstance(parsed_response, AIResponse)
        assert parsed_response.text_response == response_text
        assert parsed_response.feedback_type == FeedbackType.EXPLANATION
        assert 0.0 <= parsed_response.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_context_update(self, ai_engine, sample_context, sample_multimodal_input):
        """Test conversation context updating"""
        initial_history_length = len(sample_context.conversation_history)
        
        ai_response = AIResponse(
            text_response="Let's work through this step by step.",
            feedback_type=FeedbackType.SCAFFOLDING,
            confidence_score=0.88,
            learning_insights={
                "learning_objectives_met": ["problem_analysis", "step_by_step_thinking"]
            }
        )
        
        await ai_engine._update_context(sample_context, sample_multimodal_input, ai_response)
        
        # Check that history was updated
        assert len(sample_context.conversation_history) == initial_history_length + 2  # Student + AI
        
        # Check student entry
        student_entry = sample_context.conversation_history[-2]
        assert student_entry['type'] == 'student'
        assert student_entry['content'] == sample_multimodal_input.text_input
        assert 'modalities' in student_entry
        
        # Check AI entry
        ai_entry = sample_context.conversation_history[-1]
        assert ai_entry['type'] == 'ai'
        assert ai_entry['content'] == ai_response.text_response
        assert ai_entry['feedback_type'] == 'scaffolding'
        
        # Check learning objectives update
        assert "problem_analysis" in sample_context.learning_objectives
        assert "step_by_step_thinking" in sample_context.learning_objectives
    
    @pytest.mark.asyncio
    async def test_error_detection_mathematics(self, ai_engine, sample_context):
        """Test error detection for mathematics"""
        # Test division by zero detection
        input_with_error = "I want to divide 10 by 0 to get the answer"
        
        errors = await ai_engine._detect_common_errors(input_with_error, sample_context)
        
        assert len(errors) > 0
        division_error = next((e for e in errors if e['error_type'] == 'division_by_zero'), None)
        assert division_error is not None
        assert 'undefined' in division_error['explanation'].lower()
    
    @pytest.mark.asyncio
    async def test_context_cleanup(self, ai_engine):
        """Test expired context cleanup"""
        # Create contexts with different timestamps
        old_context = ConversationContext(
            session_id="old-session",
            user_id="user1",
            subject=SubjectArea.GENERAL,
            learning_level=LearningLevel.BEGINNER,
            conversation_history=[],
            last_interaction=datetime.utcnow() - timedelta(hours=3)  # Expired
        )
        
        recent_context = ConversationContext(
            session_id="recent-session",
            user_id="user2",
            subject=SubjectArea.GENERAL,
            learning_level=LearningLevel.BEGINNER,
            conversation_history=[],
            last_interaction=datetime.utcnow() - timedelta(minutes=30)  # Not expired
        )
        
        ai_engine.active_contexts["old-session"] = old_context
        ai_engine.active_contexts["recent-session"] = recent_context
        
        await ai_engine._cleanup_expired_contexts()
        
        assert "old-session" not in ai_engine.active_contexts
        assert "recent-session" in ai_engine.active_contexts
    
    @pytest.mark.asyncio
    async def test_learning_analytics_generation(self, ai_engine):
        """Test learning analytics generation"""
        user_id = "analytics-test-user"
        
        # Create multiple contexts for the user
        context1 = ConversationContext(
            session_id="session1",
            user_id=user_id,
            subject=SubjectArea.MATHEMATICS,
            learning_level=LearningLevel.INTERMEDIATE,
            conversation_history=[
                {'type': 'ai', 'feedback_type': 'question', 'confidence': 0.9},
                {'type': 'ai', 'feedback_type': 'encouragement', 'confidence': 0.85}
            ],
            learning_objectives=["algebra", "problem_solving"]
        )
        
        context2 = ConversationContext(
            session_id="session2",
            user_id=user_id,
            subject=SubjectArea.SCIENCE,
            learning_level=LearningLevel.INTERMEDIATE,
            conversation_history=[
                {'type': 'ai', 'feedback_type': 'explanation', 'confidence': 0.88}
            ],
            learning_objectives=["physics", "experiments"]
        )
        
        ai_engine.active_contexts["session1"] = context1
        ai_engine.active_contexts["session2"] = context2
        
        analytics = await ai_engine.get_learning_analytics(user_id)
        
        assert analytics['total_sessions'] == 2
        assert 'mathematics' in analytics['subjects_studied']
        assert 'science' in analytics['subjects_studied']
        assert 'algebra' in analytics['learning_objectives_met']
        assert 'physics' in analytics['learning_objectives_met']
        assert analytics['common_feedback_types']['question'] == 1
        assert analytics['common_feedback_types']['encouragement'] == 1
        assert analytics['common_feedback_types']['explanation'] == 1
        assert 0.8 <= analytics['average_confidence'] <= 0.9
    
    @pytest.mark.asyncio
    async def test_session_context_management(self, ai_engine, sample_context):
        """Test session context retrieval and clearing"""
        session_id = sample_context.session_id
        ai_engine.active_contexts[session_id] = sample_context
        
        # Test context retrieval
        retrieved_context = await ai_engine.get_session_context(session_id)
        assert retrieved_context is not None
        assert retrieved_context.session_id == session_id
        
        # Test context clearing
        cleared = await ai_engine.clear_session_context(session_id)
        assert cleared is True
        assert session_id not in ai_engine.active_contexts
        
        # Test clearing non-existent context
        cleared_again = await ai_engine.clear_session_context(session_id)
        assert cleared_again is False
    
    @pytest.mark.asyncio
    async def test_full_multimodal_processing_flow(self, ai_engine, sample_multimodal_input):
        """Test complete multimodal processing flow"""
        session_id = "integration-test-session"
        user_id = "integration-test-user"
        
        # Mock RAG system response
        with patch.object(ai_engine.rag_system, 'get_context_for_query', new_callable=AsyncMock) as mock_rag:
            mock_rag.return_value = {
                'context': 'Linear equations are solved by isolating the variable.',
                'sources': [{'filename': 'algebra_basics.pdf'}],
                'subjects_covered': ['mathematics'],
                'total_chunks': 1
            }
            
            # Process multimodal input
            response = await ai_engine.process_multimodal_input(
                session_id=session_id,
                user_id=user_id,
                multimodal_input=sample_multimodal_input,
                subject=SubjectArea.MATHEMATICS,
                learning_level=LearningLevel.INTERMEDIATE
            )
            
            # Verify response structure
            assert isinstance(response, AIResponse)
            assert response.text_response is not None
            assert len(response.text_response) > 0
            assert isinstance(response.feedback_type, FeedbackType)
            assert 0.0 <= response.confidence_score <= 1.0
            
            # Verify context was created and updated
            assert session_id in ai_engine.active_contexts
            context = ai_engine.active_contexts[session_id]
            assert len(context.conversation_history) >= 2  # Student input + AI response
    
    @pytest.mark.asyncio
    async def test_pedagogical_approach_selection(self, ai_engine):
        """Test that appropriate pedagogical approaches are selected"""
        # Test beginner level gets scaffolding
        beginner_context = ConversationContext(
            session_id="beginner-test",
            user_id="user1",
            subject=SubjectArea.MATHEMATICS,
            learning_level=LearningLevel.BEGINNER,
            conversation_history=[]
        )
        
        prompt = ai_engine._build_educational_prompt("test input", {}, beginner_context)
        assert "scaffolding" in prompt.lower()
        
        # Test science/math gets constructivist
        science_context = ConversationContext(
            session_id="science-test",
            user_id="user2",
            subject=SubjectArea.SCIENCE,
            learning_level=LearningLevel.INTERMEDIATE,
            conversation_history=[]
        )
        
        prompt = ai_engine._build_educational_prompt("test input", {}, science_context)
        assert "constructivist" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_response_appropriateness_validation(self, ai_engine, sample_context):
        """Test that AI responses are educationally appropriate"""
        # Test various response types
        test_responses = [
            {
                "text": "Great job! You're on the right track. What do you think the next step should be?",
                "type": "question",
                "expected_appropriate": True
            },
            {
                "text": "That's incorrect. The answer is 3. Moving on to the next problem.",
                "type": "correction",
                "expected_appropriate": False  # Too direct, not pedagogical
            },
            {
                "text": "I notice you made an error in step 2. Can you check your arithmetic there?",
                "type": "hint",
                "expected_appropriate": True
            }
        ]
        
        for test_case in test_responses:
            response_json = json.dumps({
                "text_response": test_case["text"],
                "feedback_type": test_case["type"],
                "confidence_score": 0.8
            })
            
            parsed_response = await ai_engine._parse_ai_response(response_json, sample_context)
            
            # Verify response structure is valid
            assert isinstance(parsed_response, AIResponse)
            assert parsed_response.text_response == test_case["text"]
            
            # Check for pedagogical appropriateness indicators
            if test_case["expected_appropriate"]:
                # Should contain question words or encouraging language
                text_lower = parsed_response.text_response.lower()
                has_question = any(word in text_lower for word in ['what', 'how', 'why', 'can you', 'do you'])
                has_encouragement = any(word in text_lower for word in ['great', 'good', 'nice', 'excellent'])
                has_guidance = any(word in text_lower for word in ['check', 'notice', 'think', 'consider'])
                
                assert has_question or has_encouragement or has_guidance, f"Response lacks pedagogical elements: {test_case['text']}"
    
    @pytest.mark.asyncio
    async def test_error_handling_robustness(self, ai_engine):
        """Test error handling in various scenarios"""
        # Test with empty input
        empty_input = MultimodalInput()
        response = await ai_engine.process_multimodal_input(
            session_id="error-test-1",
            user_id="error-user",
            multimodal_input=empty_input
        )
        
        assert isinstance(response, AIResponse)
        assert response.confidence_score >= 0.0
        
        # Test with malformed canvas data
        malformed_input = MultimodalInput(
            text_input="test",
            canvas_analysis=None  # This might cause issues
        )
        
        response = await ai_engine.process_multimodal_input(
            session_id="error-test-2",
            user_id="error-user",
            multimodal_input=malformed_input
        )
        
        assert isinstance(response, AIResponse)
        # Should handle gracefully without crashing
    
    def test_feedback_type_enum_coverage(self):
        """Test that all feedback types are properly defined"""
        expected_types = [
            "encouragement", "correction", "hint", 
            "explanation", "question", "validation"
        ]
        
        for expected_type in expected_types:
            assert hasattr(FeedbackType, expected_type.upper())
            assert FeedbackType(expected_type) == expected_type
    
    def test_subject_area_enum_coverage(self):
        """Test that all subject areas are properly defined"""
        expected_subjects = [
            "mathematics", "science", "language_arts", 
            "history", "general"
        ]
        
        for expected_subject in expected_subjects:
            assert hasattr(SubjectArea, expected_subject.upper())
            assert SubjectArea(expected_subject) == expected_subject
    
    def test_learning_level_enum_coverage(self):
        """Test that all learning levels are properly defined"""
        expected_levels = ["beginner", "intermediate", "advanced", "expert"]
        
        for expected_level in expected_levels:
            assert hasattr(LearningLevel, expected_level.upper())
            assert LearningLevel(expected_level) == expected_level


class TestAIResponseQuality:
    """Specific tests for AI response quality and appropriateness"""
    
    @pytest.fixture
    def ai_engine(self):
        os.environ["TESTING"] = "true"
        os.environ["GEMINI_API_KEY"] = "test-key"
        return AIReasoningEngine()
    
    def test_response_structure_validation(self):
        """Test that AIResponse objects have proper structure"""
        response = AIResponse(
            text_response="Test response",
            feedback_type=FeedbackType.QUESTION,
            confidence_score=0.85
        )
        
        assert response.text_response == "Test response"
        assert response.feedback_type == FeedbackType.QUESTION
        assert response.confidence_score == 0.85
        assert isinstance(response.whiteboard_actions, list)
        assert isinstance(response.suggested_questions, list)
        assert isinstance(response.learning_insights, dict)
        assert isinstance(response.error_corrections, list)
        assert isinstance(response.next_steps, list)
    
    def test_confidence_score_bounds(self):
        """Test that confidence scores are within valid bounds"""
        # Test valid confidence scores
        valid_scores = [0.0, 0.5, 0.99, 1.0]
        for score in valid_scores:
            response = AIResponse(
                text_response="Test",
                feedback_type=FeedbackType.EXPLANATION,
                confidence_score=score
            )
            assert 0.0 <= response.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_educational_content_filtering(self, ai_engine):
        """Test that responses are appropriate for educational context"""
        # This would be enhanced with actual content filtering logic
        sample_context = ConversationContext(
            session_id="filter-test",
            user_id="student",
            subject=SubjectArea.MATHEMATICS,
            learning_level=LearningLevel.BEGINNER,
            conversation_history=[]
        )
        
        # Test that mock responses are educationally appropriate
        mock_response = ai_engine._generate_mock_response("2+2=?", sample_context)
        response_data = json.loads(mock_response)
        
        assert "text_response" in response_data
        assert len(response_data["text_response"]) > 0
        assert response_data["feedback_type"] in [ft.value for ft in FeedbackType]
        
        # Should not contain inappropriate content
        text_lower = response_data["text_response"].lower()
        inappropriate_words = ["stupid", "wrong", "bad", "failure"]
        for word in inappropriate_words:
            assert word not in text_lower, f"Response contains inappropriate word: {word}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
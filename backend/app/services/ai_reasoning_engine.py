"""
Core AI Reasoning Engine for Multi-Galaxy-Note

This service integrates Google Gemini Pro API for natural language processing,
implements multimodal input processing, manages conversation context,
and provides pedagogical reasoning for educational feedback.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from PIL import Image
import io
import base64

from .rag_system import RAGSystem
from .computer_vision import ComputerVisionService, CanvasAnalysisResult
from .audio_processor import AudioProcessor
from .text_to_speech import TextToSpeechService, TTSResult
from .whiteboard_interaction import WhiteboardInteractionService, VisualDemonstration

logger = logging.getLogger(__name__)

class FeedbackType(str, Enum):
    """Types of educational feedback"""
    ENCOURAGEMENT = "encouragement"
    CORRECTION = "correction"
    HINT = "hint"
    EXPLANATION = "explanation"
    QUESTION = "question"
    VALIDATION = "validation"

class LearningLevel(str, Enum):
    """Student learning levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class SubjectArea(str, Enum):
    """Academic subject areas"""
    MATHEMATICS = "mathematics"
    SCIENCE = "science"
    LANGUAGE_ARTS = "language_arts"
    HISTORY = "history"
    GENERAL = "general"

@dataclass
class ConversationContext:
    """Context for maintaining conversation continuity"""
    session_id: str
    user_id: str
    subject: SubjectArea
    learning_level: LearningLevel
    conversation_history: List[Dict[str, Any]]
    current_topic: Optional[str] = None
    learning_objectives: List[str] = None
    student_progress: Dict[str, Any] = None
    last_interaction: Optional[datetime] = None
    
    def __post_init__(self):
        if self.learning_objectives is None:
            self.learning_objectives = []
        if self.student_progress is None:
            self.student_progress = {}

@dataclass
class MultimodalInput:
    """Combined input from multiple modalities"""
    text_input: Optional[str] = None
    speech_transcript: Optional[str] = None
    canvas_analysis: Optional[CanvasAnalysisResult] = None
    uploaded_documents: List[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.uploaded_documents is None:
            self.uploaded_documents = []

@dataclass
class AIResponse:
    """AI-generated response with multiple output modalities"""
    text_response: str
    feedback_type: FeedbackType
    confidence_score: float
    whiteboard_actions: List[Dict[str, Any]] = None
    suggested_questions: List[str] = None
    learning_insights: Dict[str, Any] = None
    error_corrections: List[Dict[str, Any]] = None
    next_steps: List[str] = None
    audio_response: Optional[TTSResult] = None
    visual_demonstration: Optional[VisualDemonstration] = None
    
    def __post_init__(self):
        if self.whiteboard_actions is None:
            self.whiteboard_actions = []
        if self.suggested_questions is None:
            self.suggested_questions = []
        if self.learning_insights is None:
            self.learning_insights = {}
        if self.error_corrections is None:
            self.error_corrections = []
        if self.next_steps is None:
            self.next_steps = []

class AIReasoningEngine:
    """
    Core AI reasoning engine that provides intelligent educational feedback
    using Google Gemini Pro API with multimodal capabilities
    """
    
    def __init__(self):
        """Initialize the AI reasoning engine"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            if os.getenv("TESTING") != "true":
                raise ValueError("GEMINI_API_KEY environment variable is required")
            self.api_key = "test-key"
        
        # Configure Gemini
        if self.api_key != "test-key":
            genai.configure(api_key=self.api_key)
            self.text_model = genai.GenerativeModel('gemini-pro')
            self.vision_model = genai.GenerativeModel('gemini-pro-vision')
        else:
            # Mock models for testing
            self.text_model = None
            self.vision_model = None
        
        # Initialize supporting services
        self.rag_system = RAGSystem()
        self.computer_vision = ComputerVisionService()
        self.audio_processor = AudioProcessor()
        self.tts_service = TextToSpeechService()
        self.whiteboard_service = WhiteboardInteractionService()
        
        # Context management
        self.active_contexts: Dict[str, ConversationContext] = {}
        self.context_timeout = timedelta(hours=2)  # Context expires after 2 hours
        
        # Safety settings for educational content
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        # Pedagogical templates
        self.pedagogical_prompts = {
            "socratic": """
            You are an expert educational tutor using the Socratic method. Instead of giving direct answers:
            1. Ask guiding questions that help the student discover the solution
            2. Encourage critical thinking and reasoning
            3. Build on the student's existing knowledge
            4. Provide hints only when the student is truly stuck
            5. Celebrate insights and correct reasoning
            """,
            "scaffolding": """
            You are providing scaffolded learning support. Your approach:
            1. Break complex problems into smaller, manageable steps
            2. Provide just enough support for the student to succeed
            3. Gradually reduce assistance as competence increases
            4. Connect new learning to prior knowledge
            5. Use visual and verbal explanations together
            """,
            "constructivist": """
            You are facilitating constructivist learning. Your role:
            1. Help students build their own understanding
            2. Encourage exploration and experimentation
            3. Connect learning to real-world applications
            4. Support multiple solution pathways
            5. Emphasize the learning process over just the answer
            """
        }
        
        logger.info("AI Reasoning Engine initialized with Gemini Pro")
    
    async def process_multimodal_input(
        self,
        session_id: str,
        user_id: str,
        multimodal_input: MultimodalInput,
        subject: Optional[SubjectArea] = None,
        learning_level: Optional[LearningLevel] = None
    ) -> AIResponse:
        """
        Process multimodal input and generate intelligent educational response
        
        Args:
            session_id: Learning session identifier
            user_id: User identifier
            multimodal_input: Combined input from multiple modalities
            subject: Academic subject area
            learning_level: Student's learning level
            
        Returns:
            AI-generated response with educational feedback
        """
        try:
            # Get or create conversation context
            context = await self._get_or_create_context(
                session_id, user_id, subject, learning_level
            )
            
            # Process and combine all input modalities
            combined_input = await self._combine_input_modalities(multimodal_input, context)
            
            # Retrieve relevant educational context from RAG system
            rag_context = await self._get_educational_context(combined_input, context)
            
            # Generate AI response using Gemini Pro
            ai_response = await self._generate_educational_response(
                combined_input, rag_context, context
            )
            
            # Generate TTS audio for the response
            ai_response.audio_response = await self._generate_audio_response(
                ai_response.text_response, ai_response.feedback_type.value, context
            )
            
            # Generate visual demonstration if needed
            ai_response.visual_demonstration = await self._generate_visual_demonstration(
                ai_response, combined_input, context
            )
            
            # Update conversation context
            await self._update_context(context, multimodal_input, ai_response)
            
            # Perform error detection and correction
            ai_response = await self._enhance_with_error_detection(ai_response, combined_input, context)
            
            logger.info(f"Generated AI response for session {session_id} with confidence {ai_response.confidence_score}")
            return ai_response
            
        except Exception as e:
            logger.error(f"Error processing multimodal input: {e}")
            return AIResponse(
                text_response="I apologize, but I'm having trouble processing your input right now. Could you please try again?",
                feedback_type=FeedbackType.EXPLANATION,
                confidence_score=0.0,
                error_corrections=[{"error": "processing_error", "message": str(e)}]
            )
    
    async def _get_or_create_context(
        self,
        session_id: str,
        user_id: str,
        subject: Optional[SubjectArea] = None,
        learning_level: Optional[LearningLevel] = None
    ) -> ConversationContext:
        """Get existing context or create new one"""
        
        # Clean up expired contexts
        await self._cleanup_expired_contexts()
        
        if session_id in self.active_contexts:
            context = self.active_contexts[session_id]
            context.last_interaction = datetime.utcnow()
            return context
        
        # Create new context
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            subject=subject or SubjectArea.GENERAL,
            learning_level=learning_level or LearningLevel.INTERMEDIATE,
            conversation_history=[],
            last_interaction=datetime.utcnow()
        )
        
        self.active_contexts[session_id] = context
        return context
    
    async def _combine_input_modalities(
        self,
        multimodal_input: MultimodalInput,
        context: ConversationContext
    ) -> str:
        """Combine inputs from different modalities into coherent text"""
        
        combined_parts = []
        
        # Add text input
        if multimodal_input.text_input:
            combined_parts.append(f"Text input: {multimodal_input.text_input}")
        
        # Add speech transcript
        if multimodal_input.speech_transcript:
            combined_parts.append(f"Student said: {multimodal_input.speech_transcript}")
        
        # Add canvas analysis
        if multimodal_input.canvas_analysis:
            canvas_summary = await self._summarize_canvas_content(multimodal_input.canvas_analysis)
            combined_parts.append(f"Canvas content: {canvas_summary}")
        
        # Add document context
        if multimodal_input.uploaded_documents:
            doc_summary = f"Referenced documents: {', '.join(multimodal_input.uploaded_documents)}"
            combined_parts.append(doc_summary)
        
        return "\n\n".join(combined_parts) if combined_parts else "No input detected"
    
    async def _summarize_canvas_content(self, canvas_analysis: CanvasAnalysisResult) -> str:
        """Summarize canvas analysis for input processing"""
        summary_parts = []
        
        if canvas_analysis.text_content:
            summary_parts.append(f"Text: {', '.join(canvas_analysis.text_content)}")
        
        if canvas_analysis.mathematical_equations:
            summary_parts.append(f"Math equations: {', '.join(canvas_analysis.mathematical_equations)}")
        
        if canvas_analysis.handwriting_text:
            summary_parts.append(f"Handwritten: {canvas_analysis.handwriting_text}")
        
        if canvas_analysis.diagrams:
            diagram_descriptions = [d.get('description', 'diagram') for d in canvas_analysis.diagrams]
            summary_parts.append(f"Diagrams: {', '.join(diagram_descriptions)}")
        
        return "; ".join(summary_parts) if summary_parts else "Empty canvas"
    
    async def _get_educational_context(
        self,
        combined_input: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Retrieve relevant educational context from RAG system"""
        
        try:
            # Search for relevant educational content
            rag_results = await self.rag_system.get_context_for_query(
                query=combined_input,
                user_id=context.user_id,
                subject=context.subject.value if context.subject != SubjectArea.GENERAL else None,
                max_context_length=3000
            )
            
            return {
                'relevant_content': rag_results.get('context', ''),
                'sources': rag_results.get('sources', []),
                'subjects_covered': rag_results.get('subjects_covered', []),
                'total_chunks': rag_results.get('total_chunks', 0)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving educational context: {e}")
            return {
                'relevant_content': '',
                'sources': [],
                'subjects_covered': [],
                'total_chunks': 0
            }
    
    async def _generate_educational_response(
        self,
        combined_input: str,
        rag_context: Dict[str, Any],
        context: ConversationContext
    ) -> AIResponse:
        """Generate educational response using Gemini Pro"""
        
        try:
            # Build comprehensive prompt
            prompt = self._build_educational_prompt(combined_input, rag_context, context)
            
            # Generate response using appropriate model
            if self.text_model:
                response = await asyncio.to_thread(
                    self.text_model.generate_content,
                    prompt,
                    safety_settings=self.safety_settings
                )
                response_text = response.text
            else:
                # Mock response for testing
                response_text = self._generate_mock_response(combined_input, context)
            
            # Parse structured response
            parsed_response = await self._parse_ai_response(response_text, context)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error generating educational response: {e}")
            return AIResponse(
                text_response="I'm having trouble generating a response. Let me try to help you in a different way.",
                feedback_type=FeedbackType.EXPLANATION,
                confidence_score=0.3
            )
    
    def _build_educational_prompt(
        self,
        combined_input: str,
        rag_context: Dict[str, Any],
        context: ConversationContext
    ) -> str:
        """Build comprehensive educational prompt for Gemini Pro"""
        
        # Select pedagogical approach based on context
        pedagogical_style = "socratic"  # Default to Socratic method
        if context.learning_level == LearningLevel.BEGINNER:
            pedagogical_style = "scaffolding"
        elif context.subject in [SubjectArea.SCIENCE, SubjectArea.MATHEMATICS]:
            pedagogical_style = "constructivist"
        
        base_prompt = self.pedagogical_prompts[pedagogical_style]
        
        # Build context-aware prompt
        prompt = f"""
{base_prompt}

STUDENT CONTEXT:
- Subject: {context.subject.value}
- Learning Level: {context.learning_level.value}
- Current Topic: {context.current_topic or 'Not specified'}
- Session ID: {context.session_id}

CONVERSATION HISTORY:
{self._format_conversation_history(context.conversation_history[-5:])}  # Last 5 interactions

RELEVANT EDUCATIONAL CONTENT:
{rag_context.get('relevant_content', 'No specific content found')}

CURRENT STUDENT INPUT:
{combined_input}

INSTRUCTIONS:
1. Analyze the student's input for understanding, errors, and learning opportunities
2. Provide educational feedback appropriate to their level and subject
3. Use the Socratic method to guide discovery rather than giving direct answers
4. If errors are detected, help the student identify and correct them
5. Suggest next steps or follow-up questions to deepen understanding
6. Be encouraging and supportive while maintaining academic rigor

RESPONSE FORMAT:
Please structure your response as JSON with the following fields:
{{
    "text_response": "Your main educational response to the student",
    "feedback_type": "encouragement|correction|hint|explanation|question|validation",
    "confidence_score": 0.95,
    "whiteboard_actions": [
        {{"action": "draw_line", "coordinates": [x1, y1, x2, y2], "color": "red"}},
        {{"action": "add_text", "text": "Example", "position": [x, y], "color": "blue"}}
    ],
    "suggested_questions": ["What do you think happens next?", "Can you explain your reasoning?"],
    "learning_insights": {{
        "strengths": ["Good problem setup", "Clear reasoning"],
        "areas_for_improvement": ["Check calculation", "Consider edge cases"],
        "learning_objectives_met": ["Problem solving", "Mathematical reasoning"]
    }},
    "error_corrections": [
        {{"error_type": "calculation", "location": "step 3", "correction": "2+2=4, not 5", "explanation": "Addition error"}}
    ],
    "next_steps": ["Try a similar problem", "Practice this concept", "Move to next topic"]
}}

Focus on being an excellent educational tutor who helps students learn through discovery and understanding.
"""
        
        return prompt
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for prompt context"""
        if not history:
            return "No previous conversation"
        
        formatted = []
        for entry in history:
            timestamp = entry.get('timestamp', 'Unknown time')
            if entry.get('type') == 'student':
                formatted.append(f"Student ({timestamp}): {entry.get('content', '')}")
            elif entry.get('type') == 'ai':
                formatted.append(f"AI Tutor ({timestamp}): {entry.get('content', '')}")
        
        return "\n".join(formatted)
    
    async def _parse_ai_response(self, response_text: str, context: ConversationContext) -> AIResponse:
        """Parse AI response text into structured AIResponse object"""
        
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                response_data = json.loads(json_str)
            else:
                # Fallback: create structured response from text
                response_data = {
                    "text_response": response_text,
                    "feedback_type": "explanation",
                    "confidence_score": 0.7
                }
            
            # Validate and create AIResponse
            return AIResponse(
                text_response=response_data.get('text_response', response_text),
                feedback_type=FeedbackType(response_data.get('feedback_type', 'explanation')),
                confidence_score=float(response_data.get('confidence_score', 0.7)),
                whiteboard_actions=response_data.get('whiteboard_actions', []),
                suggested_questions=response_data.get('suggested_questions', []),
                learning_insights=response_data.get('learning_insights', {}),
                error_corrections=response_data.get('error_corrections', []),
                next_steps=response_data.get('next_steps', [])
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Error parsing AI response JSON: {e}")
            # Fallback to simple response
            return AIResponse(
                text_response=response_text,
                feedback_type=FeedbackType.EXPLANATION,
                confidence_score=0.6
            )
    
    def _generate_mock_response(self, combined_input: str, context: ConversationContext) -> str:
        """Generate mock response for testing"""
        return json.dumps({
            "text_response": f"I understand you're working on {context.subject.value}. Can you tell me more about what you're trying to solve?",
            "feedback_type": "question",
            "confidence_score": 0.8,
            "suggested_questions": ["What's your approach to this problem?", "What do you already know about this topic?"],
            "learning_insights": {
                "strengths": ["Engaged with the material"],
                "areas_for_improvement": ["Need more specific input"],
                "learning_objectives_met": []
            },
            "next_steps": ["Provide more details about the problem", "Share your current understanding"]
        })
    
    async def _update_context(
        self,
        context: ConversationContext,
        multimodal_input: MultimodalInput,
        ai_response: AIResponse
    ):
        """Update conversation context with new interaction"""
        
        # Add student input to history
        if multimodal_input.text_input or multimodal_input.speech_transcript:
            student_content = multimodal_input.text_input or multimodal_input.speech_transcript
            context.conversation_history.append({
                'type': 'student',
                'content': student_content,
                'timestamp': multimodal_input.timestamp.isoformat(),
                'modalities': {
                    'text': bool(multimodal_input.text_input),
                    'speech': bool(multimodal_input.speech_transcript),
                    'canvas': bool(multimodal_input.canvas_analysis),
                    'documents': bool(multimodal_input.uploaded_documents)
                }
            })
        
        # Add AI response to history
        context.conversation_history.append({
            'type': 'ai',
            'content': ai_response.text_response,
            'timestamp': datetime.utcnow().isoformat(),
            'feedback_type': ai_response.feedback_type.value,
            'confidence': ai_response.confidence_score
        })
        
        # Update learning progress
        if ai_response.learning_insights:
            insights = ai_response.learning_insights
            if 'learning_objectives_met' in insights:
                for objective in insights['learning_objectives_met']:
                    if objective not in context.learning_objectives:
                        context.learning_objectives.append(objective)
        
        # Limit conversation history size
        if len(context.conversation_history) > 50:
            context.conversation_history = context.conversation_history[-40:]  # Keep last 40 entries
        
        context.last_interaction = datetime.utcnow()
    
    async def _enhance_with_error_detection(
        self,
        ai_response: AIResponse,
        combined_input: str,
        context: ConversationContext
    ) -> AIResponse:
        """Enhance response with error detection and correction suggestions"""
        
        try:
            # Analyze input for common educational errors
            detected_errors = await self._detect_common_errors(combined_input, context)
            
            # Add error corrections to response
            if detected_errors:
                ai_response.error_corrections.extend(detected_errors)
                
                # Adjust feedback type if errors found
                if ai_response.feedback_type == FeedbackType.VALIDATION and detected_errors:
                    ai_response.feedback_type = FeedbackType.CORRECTION
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error in error detection enhancement: {e}")
            return ai_response
    
    async def _detect_common_errors(
        self,
        combined_input: str,
        context: ConversationContext
    ) -> List[Dict[str, Any]]:
        """Detect common educational errors in student input"""
        
        errors = []
        input_lower = combined_input.lower()
        
        # Mathematics error patterns
        if context.subject == SubjectArea.MATHEMATICS:
            # Division by zero
            if 'divide' in input_lower and ('by 0' in input_lower or 'by zero' in input_lower):
                errors.append({
                    'error_type': 'division_by_zero',
                    'location': 'mathematical expression',
                    'correction': 'Division by zero is undefined',
                    'explanation': 'You cannot divide any number by zero as it results in an undefined value.'
                })
            
            # Common algebraic mistakes
            if '=' in combined_input and '+' in combined_input:
                # Simple pattern matching for equation errors
                # This would be enhanced with more sophisticated parsing
                pass
        
        # Science error patterns
        elif context.subject == SubjectArea.SCIENCE:
            # Unit confusion
            if any(unit in input_lower for unit in ['meter', 'gram', 'second']) and 'per' in input_lower:
                # Check for unit consistency
                pass
        
        # Language arts error patterns
        elif context.subject == SubjectArea.LANGUAGE_ARTS:
            # Grammar patterns
            if 'there' in input_lower and 'their' in input_lower:
                # Check for there/their/they're confusion
                pass
        
        return errors
    
    async def _generate_audio_response(
        self,
        text_response: str,
        feedback_type: str,
        context: ConversationContext
    ) -> Optional[TTSResult]:
        """Generate TTS audio for AI response"""
        
        try:
            # Generate speech using TTS service
            tts_result = await self.tts_service.synthesize_educational_response(
                text_response=text_response,
                feedback_type=feedback_type,
                context={
                    "subject": context.subject.value,
                    "learning_level": context.learning_level.value,
                    "session_id": context.session_id
                }
            )
            
            # Create audio URL for web playback
            if tts_result.audio_data:
                tts_result.audio_url = self.tts_service.create_audio_url(
                    tts_result.audio_data, tts_result.audio_format
                )
            
            return tts_result
            
        except Exception as e:
            logger.error(f"Error generating audio response: {e}")
            return None
    
    async def _generate_visual_demonstration(
        self,
        ai_response: AIResponse,
        combined_input: str,
        context: ConversationContext
    ) -> Optional[VisualDemonstration]:
        """Generate visual demonstration for complex explanations"""
        
        try:
            # Check if visual demonstration is needed
            needs_visual = await self._should_create_visual_demonstration(
                ai_response, combined_input, context
            )
            
            if not needs_visual:
                return None
            
            # Extract problem and solution steps from AI response
            problem_description = self._extract_problem_description(combined_input, ai_response)
            solution_steps = self._extract_solution_steps(ai_response)
            
            if not solution_steps:
                return None
            
            # Create visual demonstration
            demonstration = await self.whiteboard_service.create_visual_demonstration(
                problem_description=problem_description,
                solution_steps=solution_steps,
                subject_area=context.subject.value,
                canvas_size=(800, 600)
            )
            
            # Convert whiteboard actions to frontend format
            ai_response.whiteboard_actions = self.whiteboard_service.convert_actions_to_frontend_format(
                demonstration.actions
            )
            
            return demonstration
            
        except Exception as e:
            logger.error(f"Error generating visual demonstration: {e}")
            return None
    
    async def _should_create_visual_demonstration(
        self,
        ai_response: AIResponse,
        combined_input: str,
        context: ConversationContext
    ) -> bool:
        """Determine if a visual demonstration should be created"""
        
        # Check for mathematical content
        math_keywords = ["equation", "solve", "graph", "plot", "calculate", "formula"]
        has_math = any(keyword in combined_input.lower() or keyword in ai_response.text_response.lower() 
                      for keyword in math_keywords)
        
        # Check for geometry content
        geometry_keywords = ["triangle", "circle", "rectangle", "angle", "line", "point"]
        has_geometry = any(keyword in combined_input.lower() or keyword in ai_response.text_response.lower() 
                          for keyword in geometry_keywords)
        
        # Check for step-by-step explanations
        has_steps = "step" in ai_response.text_response.lower() or len(ai_response.next_steps) > 0
        
        # Check subject area
        visual_subjects = [SubjectArea.MATHEMATICS, SubjectArea.SCIENCE]
        is_visual_subject = context.subject in visual_subjects
        
        return (has_math or has_geometry or has_steps) and is_visual_subject
    
    def _extract_problem_description(self, combined_input: str, ai_response: AIResponse) -> str:
        """Extract problem description from input and response"""
        
        # Look for problem statement in input
        input_lines = combined_input.split('\n')
        for line in input_lines:
            if any(word in line.lower() for word in ["solve", "find", "calculate", "determine"]):
                return line.strip()
        
        # Fallback to first line of input
        if input_lines:
            return input_lines[0].strip()
        
        return "Problem solving"
    
    def _extract_solution_steps(self, ai_response: AIResponse) -> List[str]:
        """Extract solution steps from AI response"""
        
        steps = []
        
        # Check next_steps field
        if ai_response.next_steps:
            steps.extend(ai_response.next_steps)
        
        # Parse text response for numbered steps
        response_lines = ai_response.text_response.split('\n')
        for line in response_lines:
            line = line.strip()
            if line and (line.startswith(('1.', '2.', '3.', '4.', '5.')) or 
                        'step' in line.lower()):
                steps.append(line)
        
        # If no explicit steps found, create from response
        if not steps and len(ai_response.text_response) > 50:
            # Split response into logical chunks
            sentences = ai_response.text_response.split('. ')
            if len(sentences) > 1:
                steps = [sentence.strip() + '.' for sentence in sentences[:5]]  # Max 5 steps
        
        return steps[:5]  # Limit to 5 steps for visual clarity
    
    async def create_error_correction_visualization(
        self,
        error_location: str,
        correction_text: str,
        context: ConversationContext
    ) -> List[Dict[str, Any]]:
        """Create visual error correction on whiteboard"""
        
        try:
            # Estimate error position (this would be more sophisticated in practice)
            canvas_size = (800, 600)
            error_position = (400, 300)  # Center as default
            
            # Create error correction actions
            correction_actions = await self.whiteboard_service.create_error_correction_actions(
                error_location=error_position,
                correction_text=correction_text,
                canvas_size=canvas_size
            )
            
            # Convert to frontend format
            return self.whiteboard_service.convert_actions_to_frontend_format(correction_actions)
            
        except Exception as e:
            logger.error(f"Error creating error correction visualization: {e}")
            return []
    
    async def create_annotation_for_feedback(
        self,
        feedback_text: str,
        position: Tuple[float, float],
        feedback_type: FeedbackType
    ) -> Dict[str, Any]:
        """Create whiteboard annotation for AI feedback"""
        
        try:
            # Choose style based on feedback type
            color_map = {
                FeedbackType.ENCOURAGEMENT: "#10b981",  # Green
                FeedbackType.CORRECTION: "#ef4444",     # Red
                FeedbackType.HINT: "#f59e0b",           # Yellow
                FeedbackType.EXPLANATION: "#3b82f6",    # Blue
                FeedbackType.QUESTION: "#8b5cf6",       # Purple
                FeedbackType.VALIDATION: "#10b981"      # Green
            }
            
            from .whiteboard_interaction import DrawingStyle, AnimationStyle
            style = DrawingStyle(
                color=color_map.get(feedback_type, "#6b7280"),
                font_size=14,
                font_family="Arial"
            )
            
            # Create annotation action
            annotation = await self.whiteboard_service.create_annotation_action(
                text=feedback_text,
                position=position,
                style=style,
                animation_style=AnimationStyle.FADE_IN
            )
            
            # Convert to frontend format
            return self.whiteboard_service.convert_actions_to_frontend_format([annotation])[0]
            
        except Exception as e:
            logger.error(f"Error creating annotation: {e}")
            return {}
    
    async def _cleanup_expired_contexts(self):
        """Remove expired conversation contexts"""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, context in self.active_contexts.items():
            if context.last_interaction and (current_time - context.last_interaction) > self.context_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_contexts[session_id]
            logger.info(f"Cleaned up expired context for session {session_id}")
    
    async def get_session_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation context for a session"""
        await self._cleanup_expired_contexts()
        return self.active_contexts.get(session_id)
    
    async def clear_session_context(self, session_id: str) -> bool:
        """Clear conversation context for a session"""
        if session_id in self.active_contexts:
            del self.active_contexts[session_id]
            logger.info(f"Cleared context for session {session_id}")
            return True
        return False
    
    async def get_learning_analytics(self, user_id: str) -> Dict[str, Any]:
        """Generate learning analytics for a user across all sessions"""
        
        user_contexts = [
            context for context in self.active_contexts.values()
            if context.user_id == user_id
        ]
        
        if not user_contexts:
            return {
                'total_sessions': 0,
                'subjects_studied': [],
                'learning_objectives_met': [],
                'common_feedback_types': {},
                'average_confidence': 0.0
            }
        
        # Aggregate analytics
        subjects_studied = list(set(context.subject.value for context in user_contexts))
        all_objectives = []
        feedback_types = {}
        confidence_scores = []
        
        for context in user_contexts:
            all_objectives.extend(context.learning_objectives)
            
            for entry in context.conversation_history:
                if entry.get('type') == 'ai':
                    feedback_type = entry.get('feedback_type', 'unknown')
                    feedback_types[feedback_type] = feedback_types.get(feedback_type, 0) + 1
                    
                    if 'confidence' in entry:
                        confidence_scores.append(entry['confidence'])
        
        return {
            'total_sessions': len(user_contexts),
            'subjects_studied': subjects_studied,
            'learning_objectives_met': list(set(all_objectives)),
            'common_feedback_types': feedback_types,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
            'total_interactions': sum(len(context.conversation_history) for context in user_contexts)
        }

# Global AI reasoning engine instance
ai_reasoning_engine = AIReasoningEngine()
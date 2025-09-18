"""
Computer Vision Service for Multi-Galaxy-Note

This service handles canvas content extraction, image processing, and integration
with Google Gemini Pro Vision API for visual content analysis.
"""

import base64
import io
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import cv2
import numpy as np
from dataclasses import dataclass
import asyncio
import aiohttp
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CanvasAnalysisResult:
    """Result of canvas content analysis"""
    text_content: List[str]
    mathematical_equations: List[str]
    diagrams: List[Dict[str, Any]]
    handwriting_text: str
    confidence_scores: Dict[str, float]
    raw_analysis: str

@dataclass
class BoundingBox:
    """Bounding box for detected objects"""
    x: int
    y: int
    width: int
    height: int
    confidence: float

@dataclass
class DetectedObject:
    """Detected object on canvas"""
    type: str  # 'text', 'equation', 'diagram', 'drawing'
    content: str
    bounding_box: BoundingBox
    confidence: float

class ComputerVisionService:
    """Service for computer vision operations using Google Gemini Pro Vision"""
    
    def __init__(self):
        """Initialize the computer vision service"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            # Allow initialization without API key for testing
            if os.getenv("TESTING") != "true":
                raise ValueError("GEMINI_API_KEY environment variable is required")
            self.api_key = "test-key"
        
        # Configure Gemini
        if self.api_key != "test-key":
            genai.configure(api_key=self.api_key)
        
        # Initialize models
        if self.api_key != "test-key":
            self.vision_model = genai.GenerativeModel('gemini-pro-vision')
            self.text_model = genai.GenerativeModel('gemini-pro')
        else:
            # Mock models for testing
            self.vision_model = None
            self.text_model = None
        
        # Safety settings for educational content
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        logger.info("Computer Vision Service initialized with Gemini Pro Vision")

    async def extract_canvas_content(self, canvas_data: str) -> bytes:
        """
        Extract canvas content as image data
        
        Args:
            canvas_data: Base64 encoded canvas data or canvas JSON
            
        Returns:
            Image bytes for processing
        """
        try:
            if canvas_data.startswith('data:image'):
                # Handle base64 image data
                header, encoded = canvas_data.split(',', 1)
                image_data = base64.b64decode(encoded)
                return image_data
            else:
                # Handle Fabric.js JSON data - would need to render to image
                # For now, assume we receive base64 image data
                logger.warning("Canvas JSON rendering not implemented, expecting base64 image data")
                return b''
        except Exception as e:
            logger.error(f"Error extracting canvas content: {e}")
            raise

    async def analyze_canvas_image(self, image_data: bytes) -> CanvasAnalysisResult:
        """
        Analyze canvas image using Gemini Pro Vision
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Analysis result with detected content
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Prepare the prompt for educational content analysis
            prompt = """
            Analyze this educational whiteboard image and identify:
            
            1. **Text Content**: Any handwritten or typed text
            2. **Mathematical Equations**: Mathematical expressions, formulas, or equations
            3. **Diagrams**: Geometric shapes, scientific diagrams, charts, or drawings
            4. **Handwriting**: Convert any handwritten text to typed text
            
            Please provide your analysis in the following JSON format:
            {
                "text_content": ["list of detected text"],
                "mathematical_equations": ["list of math equations with LaTeX if possible"],
                "diagrams": [{"type": "diagram_type", "description": "description", "elements": ["list of elements"]}],
                "handwriting_text": "converted handwritten text",
                "confidence_scores": {
                    "text_detection": 0.95,
                    "equation_recognition": 0.90,
                    "diagram_analysis": 0.85,
                    "handwriting_recognition": 0.88
                }
            }
            
            Focus on educational content and be precise in mathematical notation.
            """
            
            # Generate content using Gemini Pro Vision
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [prompt, image],
                safety_settings=self.safety_settings
            )
            
            # Parse the response
            analysis_text = response.text
            
            # Try to extract JSON from the response
            try:
                # Find JSON in the response
                start_idx = analysis_text.find('{')
                end_idx = analysis_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = analysis_text[start_idx:end_idx]
                    analysis_data = json.loads(json_str)
                else:
                    # Fallback: create structured data from text
                    analysis_data = self._parse_text_analysis(analysis_text)
                
            except json.JSONDecodeError:
                # Fallback parsing
                analysis_data = self._parse_text_analysis(analysis_text)
            
            # Create result object
            result = CanvasAnalysisResult(
                text_content=analysis_data.get('text_content', []),
                mathematical_equations=analysis_data.get('mathematical_equations', []),
                diagrams=analysis_data.get('diagrams', []),
                handwriting_text=analysis_data.get('handwriting_text', ''),
                confidence_scores=analysis_data.get('confidence_scores', {}),
                raw_analysis=analysis_text
            )
            
            logger.info(f"Canvas analysis completed with {len(result.text_content)} text items, "
                       f"{len(result.mathematical_equations)} equations, {len(result.diagrams)} diagrams")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing canvas image: {e}")
            raise

    def _parse_text_analysis(self, text: str) -> Dict[str, Any]:
        """
        Fallback method to parse analysis text when JSON parsing fails
        
        Args:
            text: Raw analysis text
            
        Returns:
            Structured analysis data
        """
        # Simple text parsing fallback
        lines = text.split('\n')
        
        result = {
            'text_content': [],
            'mathematical_equations': [],
            'diagrams': [],
            'handwriting_text': '',
            'confidence_scores': {
                'text_detection': 0.7,
                'equation_recognition': 0.7,
                'diagram_analysis': 0.7,
                'handwriting_recognition': 0.7
            }
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if 'text' in line.lower() and 'content' in line.lower():
                current_section = 'text_content'
            elif 'math' in line.lower() or 'equation' in line.lower():
                current_section = 'mathematical_equations'
            elif 'diagram' in line.lower() or 'drawing' in line.lower():
                current_section = 'diagrams'
            elif 'handwriting' in line.lower():
                current_section = 'handwriting_text'
            elif line and current_section:
                if current_section == 'handwriting_text':
                    result[current_section] = line
                elif current_section == 'diagrams':
                    result[current_section].append({'type': 'unknown', 'description': line, 'elements': []})
                else:
                    result[current_section].append(line)
        
        return result

    async def recognize_mathematical_equations(self, image_data: bytes) -> List[str]:
        """
        Specialized mathematical equation recognition
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of recognized mathematical equations in LaTeX format
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            prompt = """
            Focus specifically on mathematical equations in this image.
            
            Identify and transcribe all mathematical expressions, formulas, and equations.
            Provide them in LaTeX format when possible.
            
            Examples:
            - Simple equation: x + 2 = 5 → x + 2 = 5
            - Quadratic formula: (-b ± √(b²-4ac)) / 2a → \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}
            - Integral: ∫ x dx → \\int x \\, dx
            
            Return only the mathematical expressions, one per line.
            """
            
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [prompt, image],
                safety_settings=self.safety_settings
            )
            
            # Parse equations from response
            equations = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('*'):
                    # Clean up the line
                    if '→' in line:
                        line = line.split('→')[-1].strip()
                    equations.append(line)
            
            logger.info(f"Recognized {len(equations)} mathematical equations")
            return equations
            
        except Exception as e:
            logger.error(f"Error recognizing mathematical equations: {e}")
            return []

    async def recognize_handwriting(self, image_data: bytes) -> str:
        """
        Specialized handwriting recognition
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Recognized handwritten text
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            prompt = """
            Convert all handwritten text in this image to typed text.
            
            Focus on:
            - Legible handwritten words and sentences
            - Maintain original meaning and context
            - Preserve line breaks and paragraph structure
            - Handle both cursive and print handwriting
            
            Return only the converted text, maintaining the original structure.
            """
            
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [prompt, image],
                safety_settings=self.safety_settings
            )
            
            handwriting_text = response.text.strip()
            logger.info(f"Recognized handwriting: {len(handwriting_text)} characters")
            
            return handwriting_text
            
        except Exception as e:
            logger.error(f"Error recognizing handwriting: {e}")
            return ""

    async def analyze_diagrams(self, image_data: bytes) -> List[Dict[str, Any]]:
        """
        Analyze diagrams and drawings
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of diagram analysis results
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            prompt = """
            Analyze all diagrams, drawings, and visual elements in this image.
            
            For each diagram, identify:
            - Type (geometric shape, flowchart, scientific diagram, graph, etc.)
            - Key elements and components
            - Relationships between elements
            - Educational purpose or concept being illustrated
            
            Provide analysis in JSON format:
            [
                {
                    "type": "diagram_type",
                    "description": "detailed description",
                    "elements": ["list", "of", "key", "elements"],
                    "educational_concept": "concept being taught",
                    "complexity": "simple|medium|complex"
                }
            ]
            """
            
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [prompt, image],
                safety_settings=self.safety_settings
            )
            
            # Try to parse JSON response
            try:
                # Extract JSON from response
                response_text = response.text
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    diagrams = json.loads(json_str)
                else:
                    # Fallback: create single diagram entry
                    diagrams = [{
                        'type': 'unknown',
                        'description': response_text,
                        'elements': [],
                        'educational_concept': 'unknown',
                        'complexity': 'medium'
                    }]
                    
            except json.JSONDecodeError:
                # Fallback parsing
                diagrams = [{
                    'type': 'mixed',
                    'description': response.text,
                    'elements': [],
                    'educational_concept': 'visual_content',
                    'complexity': 'medium'
                }]
            
            logger.info(f"Analyzed {len(diagrams)} diagrams")
            return diagrams
            
        except Exception as e:
            logger.error(f"Error analyzing diagrams: {e}")
            return []

    async def detect_objects_with_bounding_boxes(self, image_data: bytes) -> List[DetectedObject]:
        """
        Detect objects with bounding box information
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of detected objects with bounding boxes
        """
        try:
            # Note: Gemini Pro Vision doesn't provide bounding boxes directly
            # This is a simplified implementation that would need enhancement
            # with additional computer vision libraries for precise localization
            
            analysis_result = await self.analyze_canvas_image(image_data)
            detected_objects = []
            
            # Convert analysis results to detected objects
            # This is a simplified approach - in production, you'd want more precise localization
            
            for i, text in enumerate(analysis_result.text_content):
                detected_objects.append(DetectedObject(
                    type='text',
                    content=text,
                    bounding_box=BoundingBox(0, i*30, 200, 25, 0.8),  # Placeholder coordinates
                    confidence=analysis_result.confidence_scores.get('text_detection', 0.8)
                ))
            
            for i, equation in enumerate(analysis_result.mathematical_equations):
                detected_objects.append(DetectedObject(
                    type='equation',
                    content=equation,
                    bounding_box=BoundingBox(0, len(analysis_result.text_content)*30 + i*40, 300, 35, 0.8),
                    confidence=analysis_result.confidence_scores.get('equation_recognition', 0.8)
                ))
            
            for i, diagram in enumerate(analysis_result.diagrams):
                detected_objects.append(DetectedObject(
                    type='diagram',
                    content=diagram.get('description', ''),
                    bounding_box=BoundingBox(0, (len(analysis_result.text_content) + len(analysis_result.mathematical_equations))*35 + i*100, 400, 80, 0.8),
                    confidence=analysis_result.confidence_scores.get('diagram_analysis', 0.8)
                ))
            
            logger.info(f"Detected {len(detected_objects)} objects")
            return detected_objects
            
        except Exception as e:
            logger.error(f"Error detecting objects: {e}")
            return []

    async def process_canvas_update(self, canvas_data: str, session_context: Optional[Dict] = None) -> CanvasAnalysisResult:
        """
        Process a canvas update and return analysis results
        
        Args:
            canvas_data: Canvas data (base64 image or JSON)
            session_context: Optional session context for better analysis
            
        Returns:
            Complete analysis result
        """
        try:
            # Extract image data from canvas
            image_data = await self.extract_canvas_content(canvas_data)
            
            if not image_data:
                logger.warning("No image data extracted from canvas")
                return CanvasAnalysisResult(
                    text_content=[],
                    mathematical_equations=[],
                    diagrams=[],
                    handwriting_text='',
                    confidence_scores={},
                    raw_analysis='No content detected'
                )
            
            # Perform comprehensive analysis
            analysis_result = await self.analyze_canvas_image(image_data)
            
            logger.info("Canvas update processed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error processing canvas update: {e}")
            raise

# Global service instance
computer_vision_service = ComputerVisionService()
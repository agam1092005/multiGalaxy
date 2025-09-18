"""
Whiteboard Interaction Service for Multi-Galaxy-Note

This service handles AI drawing capabilities on the whiteboard, creating visual
demonstrations and step-by-step solutions synchronized with voice explanations.
"""

import asyncio
import logging
import json
import math
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class DrawingAction(str, Enum):
    """Types of drawing actions the AI can perform"""
    DRAW_LINE = "draw_line"
    DRAW_CIRCLE = "draw_circle"
    DRAW_RECTANGLE = "draw_rectangle"
    DRAW_ARROW = "draw_arrow"
    ADD_TEXT = "add_text"
    HIGHLIGHT = "highlight"
    ANNOTATE = "annotate"
    ERASE = "erase"
    CLEAR_AREA = "clear_area"
    MOVE_OBJECT = "move_object"

class AnimationStyle(str, Enum):
    """Animation styles for drawing actions"""
    INSTANT = "instant"
    SMOOTH = "smooth"
    STEP_BY_STEP = "step_by_step"
    FADE_IN = "fade_in"
    DRAW_ON = "draw_on"

@dataclass
class Point:
    """2D point coordinates"""
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        """Calculate distance to another point"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class DrawingStyle:
    """Style properties for drawing elements"""
    color: str = "#000000"
    stroke_width: int = 2
    fill_color: Optional[str] = None
    opacity: float = 1.0
    dash_pattern: Optional[List[int]] = None
    font_size: int = 16
    font_family: str = "Arial"
    
@dataclass
class WhiteboardAction:
    """Individual whiteboard action with timing and animation"""
    action_id: str
    action_type: DrawingAction
    coordinates: List[float]  # Flexible coordinate system
    style: DrawingStyle
    text: Optional[str] = None
    animation_style: AnimationStyle = AnimationStyle.SMOOTH
    duration_ms: int = 1000
    delay_ms: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.action_id:
            self.action_id = str(uuid.uuid4())

@dataclass
class VisualDemonstration:
    """Complete visual demonstration with synchronized actions"""
    demonstration_id: str
    title: str
    description: str
    actions: List[WhiteboardAction]
    total_duration_ms: int
    synchronized_text: List[Dict[str, Any]]  # Text synchronized with actions
    canvas_size: Tuple[int, int] = (800, 600)
    
    def __post_init__(self):
        if not self.demonstration_id:
            self.demonstration_id = str(uuid.uuid4())
        if not self.synchronized_text:
            self.synchronized_text = []

class WhiteboardInteractionService:
    """
    Service for AI-driven whiteboard interactions and visual demonstrations
    """
    
    def __init__(self):
        """Initialize the whiteboard interaction service"""
        self.active_demonstrations: Dict[str, VisualDemonstration] = {}
        self.drawing_templates = self._initialize_drawing_templates()
        self.math_symbols = self._initialize_math_symbols()
        
        logger.info("Whiteboard Interaction Service initialized")
    
    def _initialize_drawing_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common drawing templates for educational content"""
        return {
            "coordinate_system": {
                "description": "Draw coordinate axes",
                "actions": [
                    {"type": "draw_line", "coords": [400, 50, 400, 550], "style": {"color": "#333"}},  # Y-axis
                    {"type": "draw_line", "coords": [50, 300, 750, 300], "style": {"color": "#333"}},  # X-axis
                    {"type": "add_text", "coords": [760, 305], "text": "x", "style": {"font_size": 14}},
                    {"type": "add_text", "coords": [405, 40], "text": "y", "style": {"font_size": 14}}
                ]
            },
            "number_line": {
                "description": "Draw a number line",
                "actions": [
                    {"type": "draw_line", "coords": [100, 300, 700, 300], "style": {"color": "#333", "stroke_width": 2}},
                    {"type": "draw_arrow", "coords": [700, 300, 720, 300], "style": {"color": "#333"}}
                ]
            },
            "fraction_circle": {
                "description": "Draw a circle for fraction visualization",
                "actions": [
                    {"type": "draw_circle", "coords": [400, 300, 80], "style": {"color": "#333", "stroke_width": 2, "fill_color": "transparent"}}
                ]
            },
            "geometry_triangle": {
                "description": "Draw a triangle for geometry problems",
                "actions": [
                    {"type": "draw_line", "coords": [300, 400, 500, 400], "style": {"color": "#333", "stroke_width": 2}},  # Base
                    {"type": "draw_line", "coords": [500, 400, 400, 200], "style": {"color": "#333", "stroke_width": 2}},  # Right side
                    {"type": "draw_line", "coords": [400, 200, 300, 400], "style": {"color": "#333", "stroke_width": 2}}   # Left side
                ]
            }
        }
    
    def _initialize_math_symbols(self) -> Dict[str, Dict[str, Any]]:
        """Initialize mathematical symbols and their drawing instructions"""
        return {
            "plus": {"symbol": "+", "coords": [0, 0], "size": 20},
            "minus": {"symbol": "−", "coords": [0, 0], "size": 20},
            "multiply": {"symbol": "×", "coords": [0, 0], "size": 20},
            "divide": {"symbol": "÷", "coords": [0, 0], "size": 20},
            "equals": {"symbol": "=", "coords": [0, 0], "size": 20},
            "pi": {"symbol": "π", "coords": [0, 0], "size": 20},
            "theta": {"symbol": "θ", "coords": [0, 0], "size": 20},
            "alpha": {"symbol": "α", "coords": [0, 0], "size": 20},
            "beta": {"symbol": "β", "coords": [0, 0], "size": 20}
        }
    
    async def create_visual_demonstration(
        self,
        problem_description: str,
        solution_steps: List[str],
        subject_area: str = "mathematics",
        canvas_size: Tuple[int, int] = (800, 600)
    ) -> VisualDemonstration:
        """
        Create a visual demonstration for a problem solution
        
        Args:
            problem_description: Description of the problem to solve
            solution_steps: List of solution steps to visualize
            subject_area: Academic subject area
            canvas_size: Canvas dimensions
            
        Returns:
            VisualDemonstration with synchronized actions and text
        """
        
        try:
            demonstration_id = str(uuid.uuid4())
            
            # Generate actions based on subject area and problem type
            actions = await self._generate_demonstration_actions(
                problem_description, solution_steps, subject_area, canvas_size
            )
            
            # Create synchronized text explanations
            synchronized_text = await self._create_synchronized_text(solution_steps, actions)
            
            # Calculate total duration
            total_duration = sum(action.duration_ms + action.delay_ms for action in actions)
            
            demonstration = VisualDemonstration(
                demonstration_id=demonstration_id,
                title=f"Solution: {problem_description[:50]}...",
                description=problem_description,
                actions=actions,
                total_duration_ms=total_duration,
                synchronized_text=synchronized_text,
                canvas_size=canvas_size
            )
            
            # Store active demonstration
            self.active_demonstrations[demonstration_id] = demonstration
            
            logger.info(f"Created visual demonstration {demonstration_id} with {len(actions)} actions")
            return demonstration
            
        except Exception as e:
            logger.error(f"Error creating visual demonstration: {e}")
            # Return empty demonstration
            return VisualDemonstration(
                demonstration_id=str(uuid.uuid4()),
                title="Error in demonstration",
                description=problem_description,
                actions=[],
                total_duration_ms=0,
                synchronized_text=[],
                canvas_size=canvas_size
            )
    
    async def _generate_demonstration_actions(
        self,
        problem_description: str,
        solution_steps: List[str],
        subject_area: str,
        canvas_size: Tuple[int, int]
    ) -> List[WhiteboardAction]:
        """Generate whiteboard actions for the demonstration"""
        
        actions = []
        current_time = 0
        
        # Determine problem type and generate appropriate setup
        if "equation" in problem_description.lower() or "solve" in problem_description.lower():
            actions.extend(await self._create_equation_setup(canvas_size, current_time))
            current_time += 1000
        elif "graph" in problem_description.lower() or "plot" in problem_description.lower():
            actions.extend(await self._create_coordinate_system(canvas_size, current_time))
            current_time += 2000
        elif "geometry" in problem_description.lower() or "triangle" in problem_description.lower():
            actions.extend(await self._create_geometry_setup(canvas_size, current_time))
            current_time += 1500
        
        # Generate step-by-step solution actions
        for i, step in enumerate(solution_steps):
            step_actions = await self._create_step_actions(step, i, canvas_size, current_time)
            actions.extend(step_actions)
            current_time += sum(action.duration_ms + action.delay_ms for action in step_actions)
        
        return actions
    
    async def _create_equation_setup(
        self,
        canvas_size: Tuple[int, int],
        start_time: int
    ) -> List[WhiteboardAction]:
        """Create setup for equation solving"""
        
        width, height = canvas_size
        center_x, center_y = width // 2, height // 2
        
        return [
            WhiteboardAction(
                action_id=str(uuid.uuid4()),
                action_type=DrawingAction.ADD_TEXT,
                coordinates=[center_x - 100, center_y - 100],
                style=DrawingStyle(color="#333", font_size=18, font_family="Arial"),
                text="Let's solve this step by step:",
                animation_style=AnimationStyle.FADE_IN,
                duration_ms=800,
                delay_ms=start_time
            )
        ]
    
    async def _create_coordinate_system(
        self,
        canvas_size: Tuple[int, int],
        start_time: int
    ) -> List[WhiteboardAction]:
        """Create coordinate system for graphing"""
        
        width, height = canvas_size
        center_x, center_y = width // 2, height // 2
        
        actions = []
        
        # Draw axes
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.DRAW_LINE,
            coordinates=[center_x, 50, center_x, height - 50],  # Y-axis
            style=DrawingStyle(color="#333", stroke_width=2),
            animation_style=AnimationStyle.DRAW_ON,
            duration_ms=800,
            delay_ms=start_time
        ))
        
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.DRAW_LINE,
            coordinates=[50, center_y, width - 50, center_y],  # X-axis
            style=DrawingStyle(color="#333", stroke_width=2),
            animation_style=AnimationStyle.DRAW_ON,
            duration_ms=800,
            delay_ms=start_time + 400
        ))
        
        # Add axis labels
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.ADD_TEXT,
            coordinates=[width - 30, center_y + 20],
            style=DrawingStyle(color="#333", font_size=16),
            text="x",
            animation_style=AnimationStyle.FADE_IN,
            duration_ms=400,
            delay_ms=start_time + 1200
        ))
        
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.ADD_TEXT,
            coordinates=[center_x + 10, 40],
            style=DrawingStyle(color="#333", font_size=16),
            text="y",
            animation_style=AnimationStyle.FADE_IN,
            duration_ms=400,
            delay_ms=start_time + 1400
        ))
        
        return actions
    
    async def _create_geometry_setup(
        self,
        canvas_size: Tuple[int, int],
        start_time: int
    ) -> List[WhiteboardAction]:
        """Create setup for geometry problems"""
        
        width, height = canvas_size
        
        # Draw a triangle as example
        triangle_points = [
            [width // 2 - 100, height // 2 + 80],      # Bottom left
            [width // 2 + 100, height // 2 + 80],      # Bottom right
            [width // 2, height // 2 - 80]             # Top
        ]
        
        actions = []
        
        # Draw triangle sides
        for i in range(3):
            start_point = triangle_points[i]
            end_point = triangle_points[(i + 1) % 3]
            
            actions.append(WhiteboardAction(
                action_id=str(uuid.uuid4()),
                action_type=DrawingAction.DRAW_LINE,
                coordinates=[start_point[0], start_point[1], end_point[0], end_point[1]],
                style=DrawingStyle(color="#333", stroke_width=2),
                animation_style=AnimationStyle.DRAW_ON,
                duration_ms=600,
                delay_ms=start_time + i * 300
            ))
        
        return actions
    
    async def _create_step_actions(
        self,
        step_text: str,
        step_index: int,
        canvas_size: Tuple[int, int],
        start_time: int
    ) -> List[WhiteboardAction]:
        """Create actions for a single solution step"""
        
        width, height = canvas_size
        actions = []
        
        # Position for step text
        step_y = 150 + step_index * 40
        
        # Add step number and text
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.ADD_TEXT,
            coordinates=[50, step_y],
            style=DrawingStyle(color="#2563eb", font_size=16, font_family="Arial"),
            text=f"Step {step_index + 1}: {step_text}",
            animation_style=AnimationStyle.FADE_IN,
            duration_ms=800,
            delay_ms=start_time
        ))
        
        # Add visual elements based on step content
        if "=" in step_text:
            # Highlight equations
            actions.append(WhiteboardAction(
                action_id=str(uuid.uuid4()),
                action_type=DrawingAction.HIGHLIGHT,
                coordinates=[width // 2 - 50, step_y + 50, 100, 30],
                style=DrawingStyle(color="#fbbf24", opacity=0.3),
                animation_style=AnimationStyle.FADE_IN,
                duration_ms=500,
                delay_ms=start_time + 400
            ))
        
        if any(word in step_text.lower() for word in ["draw", "plot", "graph"]):
            # Add drawing indicator
            actions.append(WhiteboardAction(
                action_id=str(uuid.uuid4()),
                action_type=DrawingAction.DRAW_ARROW,
                coordinates=[width // 2 - 100, step_y + 20, width // 2, step_y + 60],
                style=DrawingStyle(color="#dc2626", stroke_width=2),
                animation_style=AnimationStyle.DRAW_ON,
                duration_ms=600,
                delay_ms=start_time + 600
            ))
        
        return actions
    
    async def _create_synchronized_text(
        self,
        solution_steps: List[str],
        actions: List[WhiteboardAction]
    ) -> List[Dict[str, Any]]:
        """Create text synchronized with whiteboard actions"""
        
        synchronized_text = []
        current_time = 0
        
        for i, step in enumerate(solution_steps):
            # Find actions for this step
            step_actions = [action for action in actions if f"Step {i + 1}" in action.text or ""]
            
            if step_actions:
                start_time = min(action.delay_ms for action in step_actions)
                end_time = max(action.delay_ms + action.duration_ms for action in step_actions)
            else:
                start_time = current_time
                end_time = current_time + 2000
            
            synchronized_text.append({
                "text": step,
                "start_time_ms": start_time,
                "end_time_ms": end_time,
                "step_index": i,
                "emphasis": "normal"
            })
            
            current_time = end_time + 500  # Small gap between steps
        
        return synchronized_text
    
    async def create_annotation_action(
        self,
        text: str,
        position: Tuple[float, float],
        style: Optional[DrawingStyle] = None,
        animation_style: AnimationStyle = AnimationStyle.FADE_IN
    ) -> WhiteboardAction:
        """Create an annotation action for AI feedback"""
        
        if not style:
            style = DrawingStyle(
                color="#dc2626",
                font_size=14,
                font_family="Arial"
            )
        
        return WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.ANNOTATE,
            coordinates=[position[0], position[1]],
            style=style,
            text=text,
            animation_style=animation_style,
            duration_ms=1000,
            delay_ms=0,
            metadata={"annotation_type": "ai_feedback"}
        )
    
    async def create_error_correction_actions(
        self,
        error_location: Tuple[float, float],
        correction_text: str,
        canvas_size: Tuple[int, int]
    ) -> List[WhiteboardAction]:
        """Create actions to show error correction"""
        
        actions = []
        
        # Highlight error area
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.HIGHLIGHT,
            coordinates=[error_location[0] - 20, error_location[1] - 10, 40, 20],
            style=DrawingStyle(color="#ef4444", opacity=0.3),
            animation_style=AnimationStyle.FADE_IN,
            duration_ms=800,
            delay_ms=0
        ))
        
        # Add correction text
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.ADD_TEXT,
            coordinates=[error_location[0], error_location[1] + 40],
            style=DrawingStyle(color="#dc2626", font_size=12),
            text=correction_text,
            animation_style=AnimationStyle.FADE_IN,
            duration_ms=1000,
            delay_ms=400
        ))
        
        # Add arrow pointing to error
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.DRAW_ARROW,
            coordinates=[error_location[0], error_location[1] + 30, error_location[0], error_location[1] + 5],
            style=DrawingStyle(color="#dc2626", stroke_width=2),
            animation_style=AnimationStyle.DRAW_ON,
            duration_ms=600,
            delay_ms=800
        ))
        
        return actions
    
    async def create_step_by_step_solution(
        self,
        equation: str,
        solution_steps: List[Dict[str, Any]],
        canvas_size: Tuple[int, int]
    ) -> VisualDemonstration:
        """Create a step-by-step solution demonstration"""
        
        demonstration_id = str(uuid.uuid4())
        actions = []
        synchronized_text = []
        current_time = 0
        
        width, height = canvas_size
        start_y = 100
        
        # Show original equation
        actions.append(WhiteboardAction(
            action_id=str(uuid.uuid4()),
            action_type=DrawingAction.ADD_TEXT,
            coordinates=[width // 2 - len(equation) * 5, start_y],
            style=DrawingStyle(color="#1f2937", font_size=20, font_family="Arial"),
            text=equation,
            animation_style=AnimationStyle.FADE_IN,
            duration_ms=1000,
            delay_ms=current_time
        ))
        
        synchronized_text.append({
            "text": f"Let's solve the equation: {equation}",
            "start_time_ms": current_time,
            "end_time_ms": current_time + 1000,
            "step_index": 0,
            "emphasis": "strong"
        })
        
        current_time += 1500
        
        # Process each solution step
        for i, step_data in enumerate(solution_steps):
            step_y = start_y + (i + 1) * 60
            
            # Show step equation
            actions.append(WhiteboardAction(
                action_id=str(uuid.uuid4()),
                action_type=DrawingAction.ADD_TEXT,
                coordinates=[width // 2 - len(step_data['equation']) * 5, step_y],
                style=DrawingStyle(color="#2563eb", font_size=18),
                text=step_data['equation'],
                animation_style=AnimationStyle.FADE_IN,
                duration_ms=800,
                delay_ms=current_time
            ))
            
            # Add explanation
            if 'explanation' in step_data:
                actions.append(WhiteboardAction(
                    action_id=str(uuid.uuid4()),
                    action_type=DrawingAction.ADD_TEXT,
                    coordinates=[50, step_y + 25],
                    style=DrawingStyle(color="#6b7280", font_size=14),
                    text=step_data['explanation'],
                    animation_style=AnimationStyle.FADE_IN,
                    duration_ms=600,
                    delay_ms=current_time + 400
                ))
            
            synchronized_text.append({
                "text": step_data.get('narration', f"Step {i + 1}: {step_data['explanation']}"),
                "start_time_ms": current_time,
                "end_time_ms": current_time + 1200,
                "step_index": i + 1,
                "emphasis": "normal"
            })
            
            current_time += 2000
        
        total_duration = current_time
        
        return VisualDemonstration(
            demonstration_id=demonstration_id,
            title=f"Solving: {equation}",
            description=f"Step-by-step solution for {equation}",
            actions=actions,
            total_duration_ms=total_duration,
            synchronized_text=synchronized_text,
            canvas_size=canvas_size
        )
    
    async def get_demonstration(self, demonstration_id: str) -> Optional[VisualDemonstration]:
        """Get a stored demonstration by ID"""
        return self.active_demonstrations.get(demonstration_id)
    
    async def clear_demonstration(self, demonstration_id: str) -> bool:
        """Clear a stored demonstration"""
        if demonstration_id in self.active_demonstrations:
            del self.active_demonstrations[demonstration_id]
            return True
        return False
    
    def convert_actions_to_frontend_format(self, actions: List[WhiteboardAction]) -> List[Dict[str, Any]]:
        """Convert whiteboard actions to frontend-compatible format"""
        
        frontend_actions = []
        
        for action in actions:
            frontend_action = {
                "id": action.action_id,
                "type": action.action_type.value,
                "coordinates": action.coordinates,
                "style": {
                    "color": action.style.color,
                    "strokeWidth": action.style.stroke_width,
                    "fillColor": action.style.fill_color,
                    "opacity": action.style.opacity,
                    "fontSize": action.style.font_size,
                    "fontFamily": action.style.font_family
                },
                "text": action.text,
                "animation": {
                    "style": action.animation_style.value,
                    "duration": action.duration_ms,
                    "delay": action.delay_ms
                },
                "metadata": action.metadata
            }
            
            frontend_actions.append(frontend_action)
        
        return frontend_actions

# Global whiteboard interaction service instance
whiteboard_interaction_service = WhiteboardInteractionService()
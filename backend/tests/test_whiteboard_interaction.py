"""
Tests for Whiteboard Interaction Service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.services.whiteboard_interaction import (
    WhiteboardInteractionService,
    WhiteboardAction,
    VisualDemonstration,
    DrawingAction,
    AnimationStyle,
    DrawingStyle,
    Point
)

class TestWhiteboardInteractionService:
    """Test cases for WhiteboardInteractionService"""
    
    @pytest.fixture
    def whiteboard_service(self):
        """Create whiteboard service instance for testing"""
        return WhiteboardInteractionService()
    
    @pytest.fixture
    def sample_drawing_style(self):
        """Sample drawing style for testing"""
        return DrawingStyle(
            color="#000000",
            stroke_width=2,
            font_size=16
        )
    
    @pytest.fixture
    def sample_whiteboard_action(self, sample_drawing_style):
        """Sample whiteboard action for testing"""
        return WhiteboardAction(
            action_id="test_action_1",
            action_type=DrawingAction.DRAW_LINE,
            coordinates=[100, 100, 200, 200],
            style=sample_drawing_style,
            animation_style=AnimationStyle.SMOOTH,
            duration_ms=1000
        )
    
    def test_point_distance_calculation(self):
        """Test Point distance calculation"""
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        
        distance = p1.distance_to(p2)
        assert distance == 5.0  # 3-4-5 triangle
    
    def test_drawing_style_defaults(self):
        """Test DrawingStyle default values"""
        style = DrawingStyle()
        
        assert style.color == "#000000"
        assert style.stroke_width == 2
        assert style.opacity == 1.0
        assert style.font_size == 16
        assert style.font_family == "Arial"
    
    def test_whiteboard_action_creation(self, sample_drawing_style):
        """Test WhiteboardAction creation and validation"""
        action = WhiteboardAction(
            action_id="",  # Should auto-generate
            action_type=DrawingAction.ADD_TEXT,
            coordinates=[100, 100],
            style=sample_drawing_style,
            text="Test text"
        )
        
        assert action.action_id != ""  # Should be auto-generated
        assert action.action_type == DrawingAction.ADD_TEXT
        assert action.coordinates == [100, 100]
        assert action.text == "Test text"
        assert action.metadata == {}
    
    def test_service_initialization(self, whiteboard_service):
        """Test service initialization"""
        assert len(whiteboard_service.drawing_templates) > 0
        assert len(whiteboard_service.math_symbols) > 0
        assert "coordinate_system" in whiteboard_service.drawing_templates
        assert "plus" in whiteboard_service.math_symbols
    
    @pytest.mark.asyncio
    async def test_create_visual_demonstration(self, whiteboard_service):
        """Test visual demonstration creation"""
        problem_description = "Solve the equation 2x + 3 = 7"
        solution_steps = [
            "Subtract 3 from both sides",
            "Divide both sides by 2",
            "x = 2"
        ]
        
        demonstration = await whiteboard_service.create_visual_demonstration(
            problem_description=problem_description,
            solution_steps=solution_steps,
            subject_area="mathematics",
            canvas_size=(800, 600)
        )
        
        assert isinstance(demonstration, VisualDemonstration)
        assert demonstration.title.startswith("Solution:")
        assert demonstration.description == problem_description
        assert len(demonstration.actions) > 0
        assert len(demonstration.synchronized_text) > 0
        assert demonstration.canvas_size == (800, 600)
    
    @pytest.mark.asyncio
    async def test_create_equation_setup(self, whiteboard_service):
        """Test equation setup creation"""
        actions = await whiteboard_service._create_equation_setup((800, 600), 0)
        
        assert len(actions) > 0
        assert any(action.action_type == DrawingAction.ADD_TEXT for action in actions)
    
    @pytest.mark.asyncio
    async def test_create_coordinate_system(self, whiteboard_service):
        """Test coordinate system creation"""
        actions = await whiteboard_service._create_coordinate_system((800, 600), 0)
        
        assert len(actions) >= 4  # Should have axes and labels
        line_actions = [a for a in actions if a.action_type == DrawingAction.DRAW_LINE]
        text_actions = [a for a in actions if a.action_type == DrawingAction.ADD_TEXT]
        
        assert len(line_actions) >= 2  # X and Y axes
        assert len(text_actions) >= 2  # X and Y labels
    
    @pytest.mark.asyncio
    async def test_create_geometry_setup(self, whiteboard_service):
        """Test geometry setup creation"""
        actions = await whiteboard_service._create_geometry_setup((800, 600), 0)
        
        assert len(actions) >= 3  # Triangle has 3 sides
        line_actions = [a for a in actions if a.action_type == DrawingAction.DRAW_LINE]
        assert len(line_actions) == 3
    
    @pytest.mark.asyncio
    async def test_create_step_actions(self, whiteboard_service):
        """Test step action creation"""
        step_text = "Step 1: Add 5 to both sides"
        actions = await whiteboard_service._create_step_actions(
            step_text, 0, (800, 600), 0
        )
        
        assert len(actions) > 0
        text_action = next((a for a in actions if a.action_type == DrawingAction.ADD_TEXT), None)
        assert text_action is not None
        assert "Step 1" in text_action.text
    
    @pytest.mark.asyncio
    async def test_create_annotation_action(self, whiteboard_service):
        """Test annotation action creation"""
        annotation = await whiteboard_service.create_annotation_action(
            text="This is a test annotation",
            position=(100, 100),
            animation_style=AnimationStyle.FADE_IN
        )
        
        assert annotation.action_type == DrawingAction.ANNOTATE
        assert annotation.text == "This is a test annotation"
        assert annotation.coordinates == [100, 100]
        assert annotation.animation_style == AnimationStyle.FADE_IN
    
    @pytest.mark.asyncio
    async def test_create_error_correction_actions(self, whiteboard_service):
        """Test error correction actions creation"""
        actions = await whiteboard_service.create_error_correction_actions(
            error_location=(200, 200),
            correction_text="The correct answer is 4, not 5",
            canvas_size=(800, 600)
        )
        
        assert len(actions) >= 3  # Highlight, text, arrow
        
        highlight_action = next((a for a in actions if a.action_type == DrawingAction.HIGHLIGHT), None)
        text_action = next((a for a in actions if a.action_type == DrawingAction.ADD_TEXT), None)
        arrow_action = next((a for a in actions if a.action_type == DrawingAction.DRAW_ARROW), None)
        
        assert highlight_action is not None
        assert text_action is not None
        assert arrow_action is not None
        assert text_action.text == "The correct answer is 4, not 5"
    
    @pytest.mark.asyncio
    async def test_create_step_by_step_solution(self, whiteboard_service):
        """Test step-by-step solution creation"""
        equation = "2x + 3 = 7"
        solution_steps = [
            {"equation": "2x + 3 - 3 = 7 - 3", "explanation": "Subtract 3 from both sides"},
            {"equation": "2x = 4", "explanation": "Simplify"},
            {"equation": "x = 2", "explanation": "Divide both sides by 2"}
        ]
        
        demonstration = await whiteboard_service.create_step_by_step_solution(
            equation=equation,
            solution_steps=solution_steps,
            canvas_size=(800, 600)
        )
        
        assert isinstance(demonstration, VisualDemonstration)
        assert equation in demonstration.title
        assert len(demonstration.actions) > 0
        assert len(demonstration.synchronized_text) > 0
    
    @pytest.mark.asyncio
    async def test_demonstration_storage_and_retrieval(self, whiteboard_service):
        """Test demonstration storage and retrieval"""
        # Create a demonstration
        demonstration = await whiteboard_service.create_visual_demonstration(
            problem_description="Test problem",
            solution_steps=["Step 1", "Step 2"],
            subject_area="mathematics"
        )
        
        demo_id = demonstration.demonstration_id
        
        # Retrieve the demonstration
        retrieved = await whiteboard_service.get_demonstration(demo_id)
        assert retrieved is not None
        assert retrieved.demonstration_id == demo_id
        
        # Clear the demonstration
        cleared = await whiteboard_service.clear_demonstration(demo_id)
        assert cleared is True
        
        # Should not be retrievable after clearing
        retrieved_after_clear = await whiteboard_service.get_demonstration(demo_id)
        assert retrieved_after_clear is None
    
    def test_convert_actions_to_frontend_format(self, whiteboard_service, sample_whiteboard_action):
        """Test conversion of actions to frontend format"""
        actions = [sample_whiteboard_action]
        
        frontend_actions = whiteboard_service.convert_actions_to_frontend_format(actions)
        
        assert len(frontend_actions) == 1
        frontend_action = frontend_actions[0]
        
        assert frontend_action["id"] == sample_whiteboard_action.action_id
        assert frontend_action["type"] == sample_whiteboard_action.action_type.value
        assert frontend_action["coordinates"] == sample_whiteboard_action.coordinates
        assert "style" in frontend_action
        assert "animation" in frontend_action
    
    @pytest.mark.asyncio
    async def test_different_subject_areas(self, whiteboard_service):
        """Test demonstration creation for different subject areas"""
        subjects = ["mathematics", "science", "geometry"]
        
        for subject in subjects:
            demonstration = await whiteboard_service.create_visual_demonstration(
                problem_description=f"Test problem for {subject}",
                solution_steps=["Step 1", "Step 2"],
                subject_area=subject
            )
            
            assert isinstance(demonstration, VisualDemonstration)
            assert len(demonstration.actions) > 0
    
    @pytest.mark.asyncio
    async def test_synchronized_text_creation(self, whiteboard_service):
        """Test synchronized text creation"""
        solution_steps = ["First step", "Second step", "Third step"]
        actions = [
            WhiteboardAction(
                action_id=f"action_{i}",
                action_type=DrawingAction.ADD_TEXT,
                coordinates=[100, 100 + i * 50],
                style=DrawingStyle(),
                text=f"Step {i + 1}: {step}",
                delay_ms=i * 1000,
                duration_ms=1000
            )
            for i, step in enumerate(solution_steps)
        ]
        
        synchronized_text = await whiteboard_service._create_synchronized_text(
            solution_steps, actions
        )
        
        assert len(synchronized_text) == len(solution_steps)
        for i, text_item in enumerate(synchronized_text):
            assert text_item["text"] == solution_steps[i]
            assert text_item["step_index"] == i
            assert "start_time_ms" in text_item
            assert "end_time_ms" in text_item

@pytest.mark.asyncio
async def test_whiteboard_service_integration():
    """Integration test for whiteboard service"""
    service = WhiteboardInteractionService()
    
    # Test complete workflow
    demonstration = await service.create_visual_demonstration(
        problem_description="Solve 3x - 6 = 9",
        solution_steps=[
            "Add 6 to both sides: 3x - 6 + 6 = 9 + 6",
            "Simplify: 3x = 15", 
            "Divide by 3: x = 5"
        ],
        subject_area="mathematics",
        canvas_size=(800, 600)
    )
    
    # Verify demonstration
    assert isinstance(demonstration, VisualDemonstration)
    assert len(demonstration.actions) > 0
    assert len(demonstration.synchronized_text) > 0
    
    # Test frontend format conversion
    frontend_actions = service.convert_actions_to_frontend_format(demonstration.actions)
    assert len(frontend_actions) == len(demonstration.actions)
    
    # Test error correction
    error_actions = await service.create_error_correction_actions(
        error_location=(300, 200),
        correction_text="Check your arithmetic",
        canvas_size=(800, 600)
    )
    assert len(error_actions) > 0
    
    # Test annotation
    annotation = await service.create_annotation_action(
        text="Good work!",
        position=(400, 100)
    )
    assert annotation.action_type == DrawingAction.ANNOTATE
    
    # Cleanup
    cleared = await service.clear_demonstration(demonstration.demonstration_id)
    assert cleared is True
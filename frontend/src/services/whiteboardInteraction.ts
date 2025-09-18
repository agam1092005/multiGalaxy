/**
 * Whiteboard Interaction service for Multi-Galaxy-Note frontend
 * 
 * Handles AI drawing capabilities and visual demonstrations on the whiteboard
 */

import { apiService } from './api';
import { Canvas } from 'fabric';

export interface WhiteboardAction {
  id: string;
  type: 'draw_line' | 'draw_circle' | 'draw_rectangle' | 'draw_arrow' | 'add_text' | 'highlight' | 'annotate' | 'erase' | 'clear_area' | 'move_object';
  coordinates: number[];
  style: {
    color: string;
    strokeWidth: number;
    fillColor?: string;
    opacity: number;
    fontSize: number;
    fontFamily: string;
  };
  text?: string;
  animation: {
    style: 'instant' | 'smooth' | 'step_by_step' | 'fade_in' | 'draw_on';
    duration: number;
    delay: number;
  };
  metadata: Record<string, any>;
}

export interface VisualDemonstration {
  demonstration_id: string;
  title: string;
  description: string;
  total_duration_ms: number;
  actions_count: number;
  synchronized_text: Array<{
    text: string;
    start_time_ms: number;
    end_time_ms: number;
    step_index: number;
    emphasis: string;
  }>;
  canvas_size: [number, number];
  created_at: string;
}

export interface VisualDemonstrationRequest {
  problem_description: string;
  solution_steps: string[];
  subject_area: string;
  canvas_width: number;
  canvas_height: number;
}

export interface ErrorCorrectionRequest {
  error_location: [number, number];
  correction_text: string;
  canvas_width: number;
  canvas_height: number;
}

export interface AnnotationRequest {
  text: string;
  position: [number, number];
  feedback_type: string;
  color?: string;
}

export interface StepBySolutionRequest {
  equation: string;
  solution_steps: Array<{
    equation: string;
    explanation: string;
    narration?: string;
  }>;
  canvas_width: number;
  canvas_height: number;
}

class WhiteboardInteractionService {
  private activeAnimations: Map<string, Animation> = new Map();
  private demonstrationCache: Map<string, VisualDemonstration> = new Map();

  /**
   * Create a visual demonstration for problem solving
   */
  async createVisualDemonstration(request: VisualDemonstrationRequest): Promise<VisualDemonstration> {
    try {
      const response = await apiService.post<VisualDemonstration>(
        '/tts-whiteboard/create-demonstration',
        request
      );
      
      // Cache the demonstration
      this.demonstrationCache.set(response.demonstration_id, response);
      
      return response;
    } catch (error) {
      console.error('Error creating visual demonstration:', error);
      throw new Error('Failed to create visual demonstration');
    }
  }

  /**
   * Get whiteboard actions for a demonstration
   */
  async getDemonstrationActions(demonstrationId: string): Promise<{
    actions: WhiteboardAction[];
    total_actions: number;
    estimated_duration_ms: number;
  }> {
    try {
      const response = await apiService.get(
        `/tts-whiteboard/demonstration/${demonstrationId}/actions`
      );
      return response;
    } catch (error) {
      console.error('Error getting demonstration actions:', error);
      throw new Error('Failed to get demonstration actions');
    }
  }

  /**
   * Create error correction visualization
   */
  async createErrorCorrection(request: ErrorCorrectionRequest): Promise<{
    actions: WhiteboardAction[];
    correction_id: string;
    total_actions: number;
    created_at: string;
  }> {
    try {
      const response = await apiService.post(
        '/tts-whiteboard/error-correction',
        request
      );
      return response;
    } catch (error) {
      console.error('Error creating error correction:', error);
      throw new Error('Failed to create error correction');
    }
  }

  /**
   * Create AI feedback annotation
   */
  async createAnnotation(request: AnnotationRequest): Promise<{
    action: WhiteboardAction;
    annotation_id: string;
    feedback_type: string;
    created_at: string;
  }> {
    try {
      const response = await apiService.post(
        '/tts-whiteboard/annotation',
        request
      );
      return response;
    } catch (error) {
      console.error('Error creating annotation:', error);
      throw new Error('Failed to create annotation');
    }
  }

  /**
   * Create step-by-step solution visualization
   */
  async createStepBySolution(request: StepBySolutionRequest): Promise<VisualDemonstration> {
    try {
      const response = await apiService.post<VisualDemonstration>(
        '/tts-whiteboard/step-by-step-solution',
        request
      );
      
      // Cache the demonstration
      this.demonstrationCache.set(response.demonstration_id, response);
      
      return response;
    } catch (error) {
      console.error('Error creating step-by-step solution:', error);
      throw new Error('Failed to create step-by-step solution');
    }
  }

  /**
   * Execute whiteboard actions on a Fabric.js canvas
   */
  async executeActions(
    canvas: Canvas,
    actions: WhiteboardAction[],
    onActionComplete?: (action: WhiteboardAction, index: number) => void,
    onAllComplete?: () => void
  ): Promise<void> {
    try {
      // Sort actions by delay time
      const sortedActions = [...actions].sort((a, b) => a.animation.delay - b.animation.delay);
      
      let completedActions = 0;
      
      for (const action of sortedActions) {
        // Schedule action execution
        setTimeout(async () => {
          await this.executeAction(canvas, action);
          completedActions++;
          
          if (onActionComplete) {
            onActionComplete(action, completedActions - 1);
          }
          
          if (completedActions === actions.length && onAllComplete) {
            onAllComplete();
          }
        }, action.animation.delay);
      }
    } catch (error) {
      console.error('Error executing whiteboard actions:', error);
      throw new Error('Failed to execute whiteboard actions');
    }
  }

  /**
   * Execute a single whiteboard action
   */
  private async executeAction(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    
    switch (action.type) {
      case 'draw_line':
        await this.drawLine(canvas, action);
        break;
      case 'draw_circle':
        await this.drawCircle(canvas, action);
        break;
      case 'draw_rectangle':
        await this.drawRectangle(canvas, action);
        break;
      case 'draw_arrow':
        await this.drawArrow(canvas, action);
        break;
      case 'add_text':
        await this.addText(canvas, action);
        break;
      case 'highlight':
        await this.addHighlight(canvas, action);
        break;
      case 'annotate':
        await this.addAnnotation(canvas, action);
        break;
      case 'erase':
        await this.eraseArea(canvas, action);
        break;
      case 'clear_area':
        await this.clearArea(canvas, action);
        break;
      default:
        console.warn(`Unknown action type: ${action.type}`);
    }
  }

  /**
   * Draw a line on the canvas
   */
  private async drawLine(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x1, y1, x2, y2] = action.coordinates;
    
    const line = new fabric.Line([x1, y1, x2, y2], {
      stroke: action.style.color,
      strokeWidth: action.style.strokeWidth,
      opacity: action.animation.style === 'fade_in' ? 0 : action.style.opacity,
      selectable: false
    });
    
    canvas.add(line);
    
    if (action.animation.style === 'fade_in') {
      this.animateFadeIn(line, action.animation.duration);
    } else if (action.animation.style === 'draw_on') {
      this.animateDrawOn(line, action.animation.duration);
    }
    
    canvas.renderAll();
  }

  /**
   * Draw a circle on the canvas
   */
  private async drawCircle(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x, y, radius] = action.coordinates;
    
    const circle = new fabric.Circle({
      left: x - radius,
      top: y - radius,
      radius: radius,
      stroke: action.style.color,
      strokeWidth: action.style.strokeWidth,
      fill: action.style.fillColor || 'transparent',
      opacity: action.animation.style === 'fade_in' ? 0 : action.style.opacity,
      selectable: false
    });
    
    canvas.add(circle);
    
    if (action.animation.style === 'fade_in') {
      this.animateFadeIn(circle, action.animation.duration);
    }
    
    canvas.renderAll();
  }

  /**
   * Draw a rectangle on the canvas
   */
  private async drawRectangle(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x, y, width, height] = action.coordinates;
    
    const rect = new fabric.Rect({
      left: x,
      top: y,
      width: width,
      height: height,
      stroke: action.style.color,
      strokeWidth: action.style.strokeWidth,
      fill: action.style.fillColor || 'transparent',
      opacity: action.animation.style === 'fade_in' ? 0 : action.style.opacity,
      selectable: false
    });
    
    canvas.add(rect);
    
    if (action.animation.style === 'fade_in') {
      this.animateFadeIn(rect, action.animation.duration);
    }
    
    canvas.renderAll();
  }

  /**
   * Draw an arrow on the canvas
   */
  private async drawArrow(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x1, y1, x2, y2] = action.coordinates;
    
    // Create arrow line
    const line = new fabric.Line([x1, y1, x2, y2], {
      stroke: action.style.color,
      strokeWidth: action.style.strokeWidth,
      opacity: action.style.opacity,
      selectable: false
    });
    
    // Calculate arrow head
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const headLength = 15;
    
    const arrowHead1 = new fabric.Line([
      x2,
      y2,
      x2 - headLength * Math.cos(angle - Math.PI / 6),
      y2 - headLength * Math.sin(angle - Math.PI / 6)
    ], {
      stroke: action.style.color,
      strokeWidth: action.style.strokeWidth,
      opacity: action.style.opacity,
      selectable: false
    });
    
    const arrowHead2 = new fabric.Line([
      x2,
      y2,
      x2 - headLength * Math.cos(angle + Math.PI / 6),
      y2 - headLength * Math.sin(angle + Math.PI / 6)
    ], {
      stroke: action.style.color,
      strokeWidth: action.style.strokeWidth,
      opacity: action.style.opacity,
      selectable: false
    });
    
    canvas.add(line, arrowHead1, arrowHead2);
    canvas.renderAll();
  }

  /**
   * Add text to the canvas
   */
  private async addText(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x, y] = action.coordinates;
    
    const text = new fabric.IText(action.text || '', {
      left: x,
      top: y,
      fontSize: action.style.fontSize,
      fontFamily: action.style.fontFamily,
      fill: action.style.color,
      opacity: action.animation.style === 'fade_in' ? 0 : action.style.opacity,
      selectable: false,
      editable: false
    });
    
    canvas.add(text);
    
    if (action.animation.style === 'fade_in') {
      this.animateFadeIn(text, action.animation.duration);
    }
    
    canvas.renderAll();
  }

  /**
   * Add highlight to the canvas
   */
  private async addHighlight(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x, y, width, height] = action.coordinates;
    
    const highlight = new fabric.Rect({
      left: x,
      top: y,
      width: width,
      height: height,
      fill: action.style.color,
      opacity: action.animation.style === 'fade_in' ? 0 : action.style.opacity,
      selectable: false
    });
    
    canvas.add(highlight);
    
    if (action.animation.style === 'fade_in') {
      this.animateFadeIn(highlight, action.animation.duration);
    }
    
    canvas.renderAll();
  }

  /**
   * Add annotation to the canvas
   */
  private async addAnnotation(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x, y] = action.coordinates;
    
    // Create annotation background
    const background = new fabric.Rect({
      left: x - 5,
      top: y - 5,
      width: (action.text?.length || 0) * 8 + 10,
      height: action.style.fontSize + 10,
      fill: '#ffffff',
      stroke: action.style.color,
      strokeWidth: 1,
      opacity: action.animation.style === 'fade_in' ? 0 : 0.9,
      selectable: false
    });
    
    // Create annotation text
    const text = new fabric.IText(action.text || '', {
      left: x,
      top: y,
      fontSize: action.style.fontSize,
      fontFamily: action.style.fontFamily,
      fill: action.style.color,
      opacity: action.animation.style === 'fade_in' ? 0 : action.style.opacity,
      selectable: false,
      editable: false
    });
    
    canvas.add(background, text);
    
    if (action.animation.style === 'fade_in') {
      this.animateFadeIn(background, action.animation.duration);
      this.animateFadeIn(text, action.animation.duration);
    }
    
    canvas.renderAll();
  }

  /**
   * Erase area on the canvas
   */
  private async eraseArea(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const [x, y, width, height] = action.coordinates;
    
    // Find objects in the erase area and remove them
    const objectsToRemove = canvas.getObjects().filter(obj => {
      const objBounds = obj.getBoundingRect();
      return (
        objBounds.left < x + width &&
        objBounds.left + objBounds.width > x &&
        objBounds.top < y + height &&
        objBounds.top + objBounds.height > y
      );
    });
    
    objectsToRemove.forEach(obj => canvas.remove(obj));
    canvas.renderAll();
  }

  /**
   * Clear specific area on the canvas
   */
  private async clearArea(canvas: Canvas, action: WhiteboardAction): Promise<void> {
    const { fabric } = await import('fabric');
    const [x, y, width, height] = action.coordinates;
    
    // Create a white rectangle to "clear" the area
    const clearRect = new fabric.Rect({
      left: x,
      top: y,
      width: width,
      height: height,
      fill: '#ffffff',
      selectable: false
    });
    
    canvas.add(clearRect);
    canvas.renderAll();
  }

  /**
   * Animate fade-in effect
   */
  private animateFadeIn(object: any, duration: number): void {
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      object.set('opacity', progress);
      object.canvas?.renderAll();
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    
    requestAnimationFrame(animate);
  }

  /**
   * Animate draw-on effect for lines
   */
  private animateDrawOn(line: any, duration: number): void {
    const originalX2 = line.x2;
    const originalY2 = line.y2;
    const startX2 = line.x1;
    const startY2 = line.y1;
    
    line.set({ x2: startX2, y2: startY2 });
    
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      const currentX2 = startX2 + (originalX2 - startX2) * progress;
      const currentY2 = startY2 + (originalY2 - startY2) * progress;
      
      line.set({ x2: currentX2, y2: currentY2 });
      line.canvas?.renderAll();
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    
    requestAnimationFrame(animate);
  }

  /**
   * Clear demonstration from cache
   */
  async clearDemonstration(demonstrationId: string): Promise<void> {
    try {
      await apiService.delete(`/tts-whiteboard/demonstration/${demonstrationId}`);
      this.demonstrationCache.delete(demonstrationId);
    } catch (error) {
      console.error('Error clearing demonstration:', error);
      throw new Error('Failed to clear demonstration');
    }
  }

  /**
   * Stop all active animations
   */
  stopAllAnimations(): void {
    this.activeAnimations.forEach(animation => {
      animation.cancel();
    });
    this.activeAnimations.clear();
  }

  /**
   * Get cached demonstration
   */
  getCachedDemonstration(demonstrationId: string): VisualDemonstration | undefined {
    return this.demonstrationCache.get(demonstrationId);
  }
}

export const whiteboardInteractionService = new WhiteboardInteractionService();
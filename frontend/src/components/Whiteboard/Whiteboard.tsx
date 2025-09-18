import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Canvas, Rect, Circle, Line, IText, FabricObject, TPointerEvent } from 'fabric';
import { WhiteboardToolbar } from './WhiteboardToolbar';
import { WhiteboardHistory } from './WhiteboardHistory';
import { webSocketService, CanvasUpdate } from '../../services/websocket';
import { ComputerVisionPanel } from '../ComputerVision/ComputerVisionPanel';
import { CanvasAnalysisResult } from '../../services/computerVision';

export interface DrawingTool {
  type: 'pen' | 'eraser' | 'rectangle' | 'circle' | 'line' | 'text';
  color: string;
  strokeWidth: number;
}

export interface WhiteboardProps {
  width?: number;
  height?: number;
  className?: string;
  sessionId?: string;
  userId?: string;
  enableRealTimeSync?: boolean;
  enableComputerVision?: boolean;
  subject?: string;
  onAnalysisComplete?: (result: CanvasAnalysisResult) => void;
}

export const Whiteboard: React.FC<WhiteboardProps> = ({ 
  width = 800, 
  height = 600, 
  className = '',
  sessionId,
  userId,
  enableRealTimeSync = false,
  enableComputerVision = false,
  subject,
  onAnalysisComplete
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [canvas, setCanvas] = useState<Canvas | null>(null);
  const [currentTool, setCurrentTool] = useState<DrawingTool>({
    type: 'pen',
    color: '#000000',
    strokeWidth: 2
  });
  const [isDrawing, setIsDrawing] = useState(false);
  const [isReceivingUpdate, setIsReceivingUpdate] = useState(false);
  const historyRef = useRef<WhiteboardHistory | null>(null);

  // Initialize canvas
  useEffect(() => {
    if (!canvasRef.current) return;

    const fabricCanvas = new Canvas(canvasRef.current, {
      width,
      height,
      backgroundColor: '#ffffff',
      selection: false,
      preserveObjectStacking: true
    });

    // Initialize history manager
    historyRef.current = new WhiteboardHistory(fabricCanvas);

    setCanvas(fabricCanvas);

    return () => {
      fabricCanvas.dispose();
    };
  }, [width, height]);

  // Real-time synchronization setup
  useEffect(() => {
    if (!canvas || !enableRealTimeSync || !sessionId || !userId) return;

    // Handle incoming canvas updates from other users
    const handleCanvasUpdate = (update: CanvasUpdate) => {
      if (update.user_id === userId) return; // Ignore own updates
      
      setIsReceivingUpdate(true);
      
      try {
        switch (update.type) {
          case 'object_added':
            if (update.data.object) {
              canvas.loadFromJSON(update.data.object, () => {
                canvas.renderAll();
                setIsReceivingUpdate(false);
              });
            }
            break;
          case 'object_modified':
            if (update.data.object && update.data.objectId) {
              const obj = canvas.getObjects().find(o => (o as any).id === update.data.objectId);
              if (obj) {
                obj.set(update.data.object);
                canvas.renderAll();
              }
            }
            setIsReceivingUpdate(false);
            break;
          case 'object_removed':
            if (update.data.objectId) {
              const obj = canvas.getObjects().find(o => (o as any).id === update.data.objectId);
              if (obj) {
                canvas.remove(obj);
                canvas.renderAll();
              }
            }
            setIsReceivingUpdate(false);
            break;
          case 'clear':
            canvas.clear();
            canvas.backgroundColor = '#ffffff';
            canvas.renderAll();
            setIsReceivingUpdate(false);
            break;
          case 'draw':
            // Handle free drawing paths
            if (update.data.path) {
              canvas.loadFromJSON({ objects: [update.data.path] }, () => {
                canvas.renderAll();
                setIsReceivingUpdate(false);
              });
            }
            break;
          default:
            setIsReceivingUpdate(false);
        }
      } catch (error) {
        console.error('Error applying canvas update:', error);
        setIsReceivingUpdate(false);
      }
    };

    // Register event listener
    webSocketService.on('canvas_update', handleCanvasUpdate);

    // Send canvas updates to other users
    const sendCanvasUpdate = (type: CanvasUpdate['type'], data: any) => {
      if (isReceivingUpdate) return; // Don't send updates while receiving
      
      const update: CanvasUpdate = {
        type,
        data,
        timestamp: new Date().toISOString()
      };
      
      webSocketService.sendCanvasUpdate(update);
    };

    // Listen for object events
    const handleObjectAdded = (e: any) => {
      if (isReceivingUpdate) return;
      
      const obj = e.target;
      if (obj && obj.type !== 'activeSelection') {
        // Assign unique ID to object
        (obj as any).id = `obj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        sendCanvasUpdate('object_added', {
          object: obj.toObject(['id'])
        });
      }
    };

    const handleObjectModified = (e: any) => {
      if (isReceivingUpdate) return;
      
      const obj = e.target;
      if (obj && (obj as any).id) {
        sendCanvasUpdate('object_modified', {
          objectId: (obj as any).id,
          object: obj.toObject(['id'])
        });
      }
    };

    const handleObjectRemoved = (e: any) => {
      if (isReceivingUpdate) return;
      
      const obj = e.target;
      if (obj && (obj as any).id) {
        sendCanvasUpdate('object_removed', {
          objectId: (obj as any).id
        });
      }
    };

    const handlePathCreated = (e: any) => {
      if (isReceivingUpdate) return;
      
      const path = e.path;
      if (path) {
        (path as any).id = `path_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        sendCanvasUpdate('draw', {
          path: path.toObject(['id'])
        });
      }
    };

    // Register canvas event listeners
    canvas.on('object:added', handleObjectAdded);
    canvas.on('object:modified', handleObjectModified);
    canvas.on('object:removed', handleObjectRemoved);
    canvas.on('path:created', handlePathCreated);

    return () => {
      webSocketService.off('canvas_update', handleCanvasUpdate);
      canvas.off('object:added', handleObjectAdded);
      canvas.off('object:modified', handleObjectModified);
      canvas.off('object:removed', handleObjectRemoved);
      canvas.off('path:created', handlePathCreated);
    };
  }, [canvas, enableRealTimeSync, sessionId, userId, isReceivingUpdate]);

  // Handle responsive canvas sizing
  useEffect(() => {
    if (!canvas) return;

    const handleResize = () => {
      const container = canvas.getElement().parentElement;
      if (!container) return;

      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      
      const scale = Math.min(
        containerWidth / width,
        containerHeight / height
      );

      canvas.setDimensions({
        width: width * scale,
        height: height * scale
      });
      canvas.setZoom(scale);
      canvas.renderAll();
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // Initial sizing

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [canvas, width, height]);

  // Configure drawing tools
  useEffect(() => {
    if (!canvas) return;

    canvas.isDrawingMode = currentTool.type === 'pen' || currentTool.type === 'eraser';
    
    if (canvas.freeDrawingBrush) {
      canvas.freeDrawingBrush.color = currentTool.type === 'eraser' ? '#ffffff' : currentTool.color;
      canvas.freeDrawingBrush.width = currentTool.strokeWidth;
    }

    // Handle shape drawing
    if (['rectangle', 'circle', 'line'].includes(currentTool.type)) {
      canvas.isDrawingMode = false;
      canvas.selection = false;
      
      let isDown = false;
      let origX = 0;
      let origY = 0;
      let shape: FabricObject | null = null;

      const handleMouseDown = (o: TPointerEvent) => {
        if (!canvas) return;
        isDown = true;
        const pointer = canvas.getPointer(o.e);
        origX = pointer.x;
        origY = pointer.y;

        // Create shape based on current tool
        switch (currentTool.type) {
          case 'rectangle':
            shape = new Rect({
              left: origX,
              top: origY,
              width: 0,
              height: 0,
              fill: 'transparent',
              stroke: currentTool.color,
              strokeWidth: currentTool.strokeWidth
            });
            break;
          case 'circle':
            shape = new Circle({
              left: origX,
              top: origY,
              radius: 0,
              fill: 'transparent',
              stroke: currentTool.color,
              strokeWidth: currentTool.strokeWidth
            });
            break;
          case 'line':
            shape = new Line([origX, origY, origX, origY], {
              stroke: currentTool.color,
              strokeWidth: currentTool.strokeWidth
            });
            break;
        }

        if (shape) {
          canvas.add(shape);
        }
      };

      const handleMouseMove = (o: TPointerEvent) => {
        if (!isDown || !shape || !canvas) return;
        
        const pointer = canvas.getPointer(o.e);
        
        switch (currentTool.type) {
          case 'rectangle':
            const rect = shape as Rect;
            rect.set({
              width: Math.abs(pointer.x - origX),
              height: Math.abs(pointer.y - origY)
            });
            if (pointer.x < origX) rect.set({ left: pointer.x });
            if (pointer.y < origY) rect.set({ top: pointer.y });
            break;
          case 'circle':
            const circle = shape as Circle;
            const radius = Math.sqrt(Math.pow(pointer.x - origX, 2) + Math.pow(pointer.y - origY, 2)) / 2;
            circle.set({ radius });
            break;
          case 'line':
            const line = shape as Line;
            line.set({ x2: pointer.x, y2: pointer.y });
            break;
        }
        
        canvas.renderAll();
      };

      const handleMouseUp = () => {
        isDown = false;
        if (shape && historyRef.current) {
          historyRef.current.saveState();
        }
        shape = null;
      };

      canvas.on('mouse:down', handleMouseDown);
      canvas.on('mouse:move', handleMouseMove);
      canvas.on('mouse:up', handleMouseUp);

      return () => {
        canvas.off('mouse:down', handleMouseDown);
        canvas.off('mouse:move', handleMouseMove);
        canvas.off('mouse:up', handleMouseUp);
      };
    }
  }, [canvas, currentTool]);

  // Save state after drawing
  useEffect(() => {
    if (!canvas || !historyRef.current) return;

    const handlePathCreated = () => {
      historyRef.current?.saveState();
    };

    canvas.on('path:created', handlePathCreated);

    return () => {
      canvas.off('path:created', handlePathCreated);
    };
  }, [canvas]);

  const handleToolChange = useCallback((tool: DrawingTool) => {
    setCurrentTool(tool);
  }, []);

  const handleUndo = useCallback(() => {
    historyRef.current?.undo();
  }, []);

  const handleRedo = useCallback(() => {
    historyRef.current?.redo();
  }, []);

  const handleClear = useCallback(() => {
    if (canvas) {
      canvas.clear();
      canvas.backgroundColor = '#ffffff';
      canvas.renderAll();
      historyRef.current?.saveState();
      
      // Send clear update to other users
      if (enableRealTimeSync && !isReceivingUpdate) {
        const update: CanvasUpdate = {
          type: 'clear',
          data: {},
          timestamp: new Date().toISOString()
        };
        webSocketService.sendCanvasUpdate(update);
      }
    }
  }, [canvas, enableRealTimeSync, isReceivingUpdate]);

  const handleAddText = useCallback(() => {
    if (!canvas) return;

    const text = new IText('Click to edit', {
      left: 100,
      top: 100,
      fontFamily: 'Arial',
      fontSize: 20,
      fill: currentTool.color
    });

    canvas.add(text);
    canvas.setActiveObject(text);
    text.enterEditing();
    historyRef.current?.saveState();
  }, [canvas, currentTool.color]);

  return (
    <div className={`whiteboard-container ${className}`}>
      <WhiteboardToolbar
        currentTool={currentTool}
        onToolChange={handleToolChange}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onClear={handleClear}
        onAddText={handleAddText}
        canUndo={historyRef.current?.canUndo() ?? false}
        canRedo={historyRef.current?.canRedo() ?? false}
      />
      <div className="flex gap-4">
        <div className="canvas-container bg-white border border-gray-300 rounded-lg shadow-lg overflow-hidden">
          <canvas ref={canvasRef} />
        </div>
        {enableComputerVision && (
          <div className="w-80">
            <ComputerVisionPanel
              canvas={canvas}
              sessionId={sessionId}
              subject={subject}
              onAnalysisComplete={onAnalysisComplete}
              className="h-fit"
            />
          </div>
        )}
      </div>
    </div>
  );
};
import React from 'react';
import { DrawingTool } from './Whiteboard';

interface WhiteboardToolbarProps {
  currentTool: DrawingTool;
  onToolChange: (tool: DrawingTool) => void;
  onUndo: () => void;
  onRedo: () => void;
  onClear: () => void;
  onAddText: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

export const WhiteboardToolbar: React.FC<WhiteboardToolbarProps> = ({
  currentTool,
  onToolChange,
  onUndo,
  onRedo,
  onClear,
  onAddText,
  canUndo,
  canRedo
}) => {
  const tools = [
    { type: 'pen' as const, icon: '✏️', label: 'Pen' },
    { type: 'eraser' as const, icon: '🧽', label: 'Eraser' },
    { type: 'rectangle' as const, icon: '⬜', label: 'Rectangle' },
    { type: 'circle' as const, icon: '⭕', label: 'Circle' },
    { type: 'line' as const, icon: '📏', label: 'Line' }
  ];

  const colors = [
    '#000000', '#FF0000', '#00FF00', '#0000FF',
    '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500',
    '#800080', '#008000', '#800000', '#000080'
  ];

  const strokeWidths = [1, 2, 4, 6, 8, 12];

  const handleToolSelect = (toolType: DrawingTool['type']) => {
    onToolChange({
      ...currentTool,
      type: toolType
    });
  };

  const handleColorSelect = (color: string) => {
    onToolChange({
      ...currentTool,
      color
    });
  };

  const handleStrokeWidthSelect = (strokeWidth: number) => {
    onToolChange({
      ...currentTool,
      strokeWidth
    });
  };

  return (
    <div className="whiteboard-toolbar bg-gray-100 p-4 border-b border-gray-300 flex flex-wrap items-center gap-4">
      {/* Drawing Tools */}
      <div className="tool-group flex gap-2">
        <span className="text-sm font-medium text-gray-700 self-center">Tools:</span>
        {tools.map((tool) => (
          <button
            key={tool.type}
            onClick={() => handleToolSelect(tool.type)}
            className={`tool-button px-3 py-2 rounded-md border transition-colors ${
              currentTool.type === tool.type
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
            title={tool.label}
          >
            <span className="text-lg">{tool.icon}</span>
          </button>
        ))}
        <button
          onClick={onAddText}
          className="tool-button px-3 py-2 rounded-md border bg-white text-gray-700 border-gray-300 hover:bg-gray-50 transition-colors"
          title="Add Text"
        >
          <span className="text-lg">📝</span>
        </button>
      </div>

      {/* Color Picker */}
      <div className="tool-group flex gap-2">
        <span className="text-sm font-medium text-gray-700 self-center">Color:</span>
        <div className="flex gap-1">
          {colors.map((color) => (
            <button
              key={color}
              onClick={() => handleColorSelect(color)}
              className={`w-8 h-8 rounded border-2 transition-transform hover:scale-110 ${
                currentTool.color === color ? 'border-gray-800' : 'border-gray-300'
              }`}
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
        </div>
        <input
          type="color"
          value={currentTool.color}
          onChange={(e) => handleColorSelect(e.target.value)}
          className="w-8 h-8 rounded border border-gray-300 cursor-pointer"
          title="Custom Color"
        />
      </div>

      {/* Stroke Width */}
      <div className="tool-group flex gap-2">
        <span className="text-sm font-medium text-gray-700 self-center">Size:</span>
        <select
          value={currentTool.strokeWidth}
          onChange={(e) => handleStrokeWidthSelect(Number(e.target.value))}
          className="px-2 py-1 border border-gray-300 rounded-md bg-white text-gray-700"
        >
          {strokeWidths.map((width) => (
            <option key={width} value={width}>
              {width}px
            </option>
          ))}
        </select>
      </div>

      {/* History Controls */}
      <div className="tool-group flex gap-2 ml-auto">
        <button
          onClick={onUndo}
          disabled={!canUndo}
          className={`px-3 py-2 rounded-md border transition-colors ${
            canUndo
              ? 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              : 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
          }`}
          title="Undo"
        >
          ↶ Undo
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          className={`px-3 py-2 rounded-md border transition-colors ${
            canRedo
              ? 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              : 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
          }`}
          title="Redo"
        >
          ↷ Redo
        </button>
        <button
          onClick={onClear}
          className="px-3 py-2 rounded-md border bg-red-500 text-white border-red-500 hover:bg-red-600 transition-colors"
          title="Clear Canvas"
        >
          🗑️ Clear
        </button>
      </div>
    </div>
  );
};
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { WhiteboardToolbar } from '../WhiteboardToolbar';
import { DrawingTool } from '../Whiteboard';

// Test the toolbar component separately since it's easier to test
// The main Whiteboard component requires complex fabric.js mocking

describe('Whiteboard Integration Tests', () => {
  const mockProps = {
    currentTool: {
      type: 'pen' as const,
      color: '#000000',
      strokeWidth: 2
    } as DrawingTool,
    onToolChange: jest.fn(),
    onUndo: jest.fn(),
    onRedo: jest.fn(),
    onClear: jest.fn(),
    onAddText: jest.fn(),
    canUndo: false,
    canRedo: false
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('toolbar renders with all required tools', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    expect(screen.getByTitle('Pen')).toBeInTheDocument();
    expect(screen.getByTitle('Eraser')).toBeInTheDocument();
    expect(screen.getByTitle('Rectangle')).toBeInTheDocument();
    expect(screen.getByTitle('Circle')).toBeInTheDocument();
    expect(screen.getByTitle('Line')).toBeInTheDocument();
    expect(screen.getByTitle('Add Text')).toBeInTheDocument();
  });

  test('toolbar shows current tool as selected', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const penButton = screen.getByTitle('Pen');
    expect(penButton).toHaveClass('bg-blue-500');
  });

  test('toolbar has color picker functionality', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const customColorInput = screen.getByTitle('Custom Color');
    expect(customColorInput).toBeInTheDocument();
    expect(customColorInput).toHaveAttribute('type', 'color');
  });

  test('toolbar has stroke width selector', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const sizeSelect = screen.getByDisplayValue('2px');
    expect(sizeSelect).toBeInTheDocument();
  });

  test('toolbar has history controls', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    expect(screen.getByText(/undo/i)).toBeInTheDocument();
    expect(screen.getByText(/redo/i)).toBeInTheDocument();
    expect(screen.getByText(/clear/i)).toBeInTheDocument();
  });

  test('undo and redo buttons are disabled when no history', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    expect(screen.getByText(/undo/i)).toBeDisabled();
    expect(screen.getByText(/redo/i)).toBeDisabled();
  });

  test('undo and redo buttons are enabled when history is available', () => {
    render(<WhiteboardToolbar {...mockProps} canUndo={true} canRedo={true} />);
    
    expect(screen.getByText(/undo/i)).not.toBeDisabled();
    expect(screen.getByText(/redo/i)).not.toBeDisabled();
  });
});
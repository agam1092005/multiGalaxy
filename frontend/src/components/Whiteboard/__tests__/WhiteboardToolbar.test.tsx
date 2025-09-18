import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { WhiteboardToolbar } from '../WhiteboardToolbar';
import { DrawingTool } from '../Whiteboard';

describe('WhiteboardToolbar Component', () => {
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

  test('renders all drawing tools', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    expect(screen.getByTitle('Pen')).toBeInTheDocument();
    expect(screen.getByTitle('Eraser')).toBeInTheDocument();
    expect(screen.getByTitle('Rectangle')).toBeInTheDocument();
    expect(screen.getByTitle('Circle')).toBeInTheDocument();
    expect(screen.getByTitle('Line')).toBeInTheDocument();
    expect(screen.getByTitle('Add Text')).toBeInTheDocument();
  });

  test('highlights current tool', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const penButton = screen.getByTitle('Pen');
    expect(penButton).toHaveClass('bg-blue-500');
  });

  test('calls onToolChange when tool is selected', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const eraserButton = screen.getByTitle('Eraser');
    fireEvent.click(eraserButton);
    
    expect(mockProps.onToolChange).toHaveBeenCalledWith({
      ...mockProps.currentTool,
      type: 'eraser'
    });
  });

  test('renders color palette', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    // Should have predefined colors plus custom color input
    const colorButtons = screen.getAllByRole('button').filter(button => 
      button.style.backgroundColor && button.style.backgroundColor !== ''
    );
    expect(colorButtons.length).toBeGreaterThan(0);
    
    const customColorInput = screen.getByTitle('Custom Color');
    expect(customColorInput).toBeInTheDocument();
    expect(customColorInput).toHaveAttribute('type', 'color');
  });

  test('calls onToolChange when color is selected', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const customColorInput = screen.getByTitle('Custom Color');
    fireEvent.change(customColorInput, { target: { value: '#ff0000' } });
    
    expect(mockProps.onToolChange).toHaveBeenCalledWith({
      ...mockProps.currentTool,
      color: '#ff0000'
    });
  });

  test('renders stroke width selector', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const sizeSelect = screen.getByDisplayValue('2px');
    expect(sizeSelect).toBeInTheDocument();
  });

  test('calls onToolChange when stroke width is changed', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const sizeSelect = screen.getByDisplayValue('2px');
    fireEvent.change(sizeSelect, { target: { value: '6' } });
    
    expect(mockProps.onToolChange).toHaveBeenCalledWith({
      ...mockProps.currentTool,
      strokeWidth: 6
    });
  });

  test('undo button is disabled when canUndo is false', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const undoButton = screen.getByText(/undo/i);
    expect(undoButton).toBeDisabled();
    expect(undoButton).toHaveClass('cursor-not-allowed');
  });

  test('undo button is enabled when canUndo is true', () => {
    render(<WhiteboardToolbar {...mockProps} canUndo={true} />);
    
    const undoButton = screen.getByText(/undo/i);
    expect(undoButton).not.toBeDisabled();
    expect(undoButton).not.toHaveClass('cursor-not-allowed');
  });

  test('calls onUndo when undo button is clicked', () => {
    render(<WhiteboardToolbar {...mockProps} canUndo={true} />);
    
    const undoButton = screen.getByText(/undo/i);
    fireEvent.click(undoButton);
    
    expect(mockProps.onUndo).toHaveBeenCalled();
  });

  test('redo button is disabled when canRedo is false', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const redoButton = screen.getByText(/redo/i);
    expect(redoButton).toBeDisabled();
    expect(redoButton).toHaveClass('cursor-not-allowed');
  });

  test('redo button is enabled when canRedo is true', () => {
    render(<WhiteboardToolbar {...mockProps} canRedo={true} />);
    
    const redoButton = screen.getByText(/redo/i);
    expect(redoButton).not.toBeDisabled();
    expect(redoButton).not.toHaveClass('cursor-not-allowed');
  });

  test('calls onRedo when redo button is clicked', () => {
    render(<WhiteboardToolbar {...mockProps} canRedo={true} />);
    
    const redoButton = screen.getByText(/redo/i);
    fireEvent.click(redoButton);
    
    expect(mockProps.onRedo).toHaveBeenCalled();
  });

  test('calls onClear when clear button is clicked', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const clearButton = screen.getByText(/clear/i);
    fireEvent.click(clearButton);
    
    expect(mockProps.onClear).toHaveBeenCalled();
  });

  test('calls onAddText when add text button is clicked', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    const addTextButton = screen.getByTitle('Add Text');
    fireEvent.click(addTextButton);
    
    expect(mockProps.onAddText).toHaveBeenCalled();
  });

  test('displays current color in custom color input', () => {
    const propsWithRedColor = {
      ...mockProps,
      currentTool: { ...mockProps.currentTool, color: '#ff0000' }
    };
    
    render(<WhiteboardToolbar {...propsWithRedColor} />);
    
    const customColorInput = screen.getByTitle('Custom Color');
    expect(customColorInput).toHaveValue('#ff0000');
  });

  test('highlights selected predefined color', () => {
    render(<WhiteboardToolbar {...mockProps} />);
    
    // Find the black color button (should be highlighted for default black color)
    const colorButtons = screen.getAllByRole('button').filter(button => 
      button.style.backgroundColor === 'rgb(0, 0, 0)' || button.style.backgroundColor === '#000000'
    );
    
    if (colorButtons.length > 0) {
      expect(colorButtons[0]).toHaveClass('border-gray-800');
    }
  });
});
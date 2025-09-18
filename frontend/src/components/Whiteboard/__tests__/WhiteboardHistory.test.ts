import { WhiteboardHistory } from '../WhiteboardHistory';

// Mock fabric.js Canvas
const mockCanvas = {
  toJSON: jest.fn(),
  loadFromJSON: jest.fn(),
  renderAll: jest.fn()
};

describe('WhiteboardHistory', () => {
  let history: WhiteboardHistory;

  beforeEach(() => {
    jest.clearAllMocks();
    mockCanvas.toJSON.mockReturnValue({ objects: [] });
    history = new WhiteboardHistory(mockCanvas as any);
  });

  test('initializes with empty state saved', () => {
    expect(mockCanvas.toJSON).toHaveBeenCalled();
    expect(history.getHistorySize()).toBe(1);
    expect(history.getCurrentIndex()).toBe(0);
  });

  test('cannot undo initially', () => {
    expect(history.canUndo()).toBe(false);
  });

  test('cannot redo initially', () => {
    expect(history.canRedo()).toBe(false);
  });

  test('saves new state', () => {
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect' }] });
    
    history.saveState();
    
    expect(history.getHistorySize()).toBe(2);
    expect(history.getCurrentIndex()).toBe(1);
    expect(history.canUndo()).toBe(true);
    expect(history.canRedo()).toBe(false);
  });

  test('performs undo operation', () => {
    // Add a state to have something to undo
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect' }] });
    history.saveState();
    
    const undoResult = history.undo();
    
    expect(undoResult).toBe(true);
    expect(mockCanvas.loadFromJSON).toHaveBeenCalled();
    expect(history.getCurrentIndex()).toBe(0);
    expect(history.canUndo()).toBe(false);
    expect(history.canRedo()).toBe(true);
  });

  test('cannot undo when at beginning of history', () => {
    const undoResult = history.undo();
    
    expect(undoResult).toBe(false);
    expect(mockCanvas.loadFromJSON).not.toHaveBeenCalled();
  });

  test('performs redo operation', () => {
    // Add a state and undo to have something to redo
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect' }] });
    history.saveState();
    history.undo();
    
    const redoResult = history.redo();
    
    expect(redoResult).toBe(true);
    expect(mockCanvas.loadFromJSON).toHaveBeenCalledTimes(2); // Once for undo, once for redo
    expect(history.getCurrentIndex()).toBe(1);
    expect(history.canUndo()).toBe(true);
    expect(history.canRedo()).toBe(false);
  });

  test('cannot redo when at end of history', () => {
    const redoResult = history.redo();
    
    expect(redoResult).toBe(false);
    expect(mockCanvas.loadFromJSON).not.toHaveBeenCalled();
  });

  test('clears history after undo and new save', () => {
    // Create some history
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect' }] });
    history.saveState();
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'circle' }] });
    history.saveState();
    
    expect(history.getHistorySize()).toBe(3);
    
    // Undo once
    history.undo();
    expect(history.canRedo()).toBe(true);
    
    // Save new state (should clear redo history)
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'line' }] });
    history.saveState();
    
    expect(history.canRedo()).toBe(false);
    expect(history.getHistorySize()).toBe(3); // Should have removed the future state
  });

  test('limits history size', () => {
    // Create more states than the max history size (50)
    for (let i = 0; i < 60; i++) {
      mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect', id: i }] });
      history.saveState();
    }
    
    expect(history.getHistorySize()).toBeLessThanOrEqual(50);
    expect(history.getCurrentIndex()).toBeLessThanOrEqual(49);
  });

  test('clears all history', () => {
    // Add some states
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect' }] });
    history.saveState();
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'circle' }] });
    history.saveState();
    
    history.clear();
    
    expect(history.getHistorySize()).toBe(1); // Should have one state (the cleared state)
    expect(history.getCurrentIndex()).toBe(0);
    expect(history.canUndo()).toBe(false);
    expect(history.canRedo()).toBe(false);
  });

  test('calls renderAll after loading state', () => {
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect' }] });
    history.saveState();
    
    mockCanvas.loadFromJSON.mockImplementation((state, callback) => {
      callback();
    });
    
    history.undo();
    
    expect(mockCanvas.renderAll).toHaveBeenCalled();
  });

  test('handles loadFromJSON callback properly', () => {
    mockCanvas.toJSON.mockReturnValue({ objects: [{ type: 'rect' }] });
    history.saveState();
    
    let callbackCalled = false;
    mockCanvas.loadFromJSON.mockImplementation((state, callback) => {
      if (callback) {
        callback();
        callbackCalled = true;
      }
    });
    
    history.undo();
    
    expect(callbackCalled).toBe(true);
  });
});
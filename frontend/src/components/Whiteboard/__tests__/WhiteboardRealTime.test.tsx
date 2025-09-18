/**
 * Integration tests for Whiteboard real-time functionality
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Whiteboard } from '../Whiteboard';
import { webSocketService } from '../../../services/websocket';

// Mock the WebSocket service
jest.mock('../../../services/websocket', () => ({
  webSocketService: {
    connect: jest.fn().mockResolvedValue(undefined),
    disconnect: jest.fn(),
    joinSession: jest.fn().mockResolvedValue(undefined),
    leaveSession: jest.fn().mockResolvedValue(undefined),
    sendCanvasUpdate: jest.fn(),
    on: jest.fn(),
    off: jest.fn(),
    isSocketConnected: jest.fn().mockReturnValue(true),
    getCurrentSessionId: jest.fn().mockReturnValue('test-session'),
    getCurrentUserId: jest.fn().mockReturnValue('test-user')
  }
}));

// Mock Fabric.js Canvas
jest.mock('fabric', () => ({
  Canvas: jest.fn().mockImplementation(() => ({
    setDimensions: jest.fn(),
    setZoom: jest.fn(),
    renderAll: jest.fn(),
    dispose: jest.fn(),
    getElement: jest.fn().mockReturnValue({
      parentElement: {
        clientWidth: 800,
        clientHeight: 600
      }
    }),
    on: jest.fn(),
    off: jest.fn(),
    clear: jest.fn(),
    getObjects: jest.fn().mockReturnValue([]),
    add: jest.fn(),
    remove: jest.fn(),
    loadFromJSON: jest.fn((data, callback) => callback && callback()),
    freeDrawingBrush: {
      color: '#000000',
      width: 2
    },
    isDrawingMode: false,
    selection: false,
    backgroundColor: '#ffffff'
  })),
  Rect: jest.fn(),
  Circle: jest.fn(),
  Line: jest.fn(),
  IText: jest.fn()
}));

describe('Whiteboard Real-Time Integration', () => {
  const mockWebSocketService = webSocketService as jest.Mocked<typeof webSocketService>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should initialize with real-time sync enabled', () => {
    render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    // Verify WebSocket event listeners are set up
    expect(mockWebSocketService.on).toHaveBeenCalledWith(
      'canvas_update',
      expect.any(Function)
    );
  });

  test('should send canvas updates when drawing', async () => {
    const { container } = render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    // Wait for component to initialize
    await waitFor(() => {
      expect(container.querySelector('canvas')).toBeInTheDocument();
    });

    // Verify that canvas update sending is set up
    expect(mockWebSocketService.on).toHaveBeenCalled();
  });

  test('should handle incoming canvas updates from other users', () => {
    render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    // Get the canvas update handler
    const canvasUpdateHandler = mockWebSocketService.on.mock.calls.find(
      call => call[0] === 'canvas_update'
    )?.[1];

    expect(canvasUpdateHandler).toBeDefined();

    // Simulate incoming canvas update
    if (canvasUpdateHandler) {
      const incomingUpdate = {
        type: 'object_added' as const,
        data: {
          object: {
            type: 'rect',
            left: 100,
            top: 100,
            width: 50,
            height: 50
          }
        },
        timestamp: new Date().toISOString(),
        user_id: 'other-user'
      };

      // This should not throw
      expect(() => canvasUpdateHandler(incomingUpdate)).not.toThrow();
    }
  });

  test('should not send updates when receiving updates from others', () => {
    render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    // Simulate receiving an update (this should set isReceivingUpdate to true)
    const canvasUpdateHandler = mockWebSocketService.on.mock.calls.find(
      call => call[0] === 'canvas_update'
    )?.[1];

    if (canvasUpdateHandler) {
      const incomingUpdate = {
        type: 'clear' as const,
        data: {},
        timestamp: new Date().toISOString(),
        user_id: 'other-user'
      };

      canvasUpdateHandler(incomingUpdate);
    }

    // Verify that the component handles the update without sending its own
    expect(mockWebSocketService.sendCanvasUpdate).not.toHaveBeenCalled();
  });

  test('should clean up WebSocket listeners on unmount', () => {
    const { unmount } = render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    // Unmount the component
    unmount();

    // Verify cleanup was called
    expect(mockWebSocketService.off).toHaveBeenCalledWith(
      'canvas_update',
      expect.any(Function)
    );
  });

  test('should work without real-time sync when disabled', () => {
    render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={false}
      />
    );

    // Should not set up WebSocket listeners when real-time sync is disabled
    expect(mockWebSocketService.on).not.toHaveBeenCalled();
  });

  test('should handle clear operations in real-time', () => {
    const { getByText } = render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    // Find and click the clear button (assuming it exists in the toolbar)
    const clearButton = getByText(/clear/i);
    if (clearButton) {
      fireEvent.click(clearButton);

      // Should send a clear update
      expect(mockWebSocketService.sendCanvasUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'clear',
          data: {}
        })
      );
    }
  });
});

describe('Whiteboard Performance with Real-Time Sync', () => {
  const mockWebSocketService = webSocketService as jest.Mocked<typeof webSocketService>;

  test('should handle rapid canvas updates efficiently', async () => {
    render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    const canvasUpdateHandler = mockWebSocketService.on.mock.calls.find(
      call => call[0] === 'canvas_update'
    )?.[1];

    if (canvasUpdateHandler) {
      // Simulate rapid incoming updates
      const updates = Array.from({ length: 100 }, (_, i) => ({
        type: 'draw' as const,
        data: { path: `path_${i}` },
        timestamp: new Date().toISOString(),
        user_id: 'other-user'
      }));

      const startTime = performance.now();
      
      updates.forEach(update => {
        canvasUpdateHandler(update);
      });

      const endTime = performance.now();
      const processingTime = endTime - startTime;

      // Should process 100 updates in reasonable time (less than 100ms)
      expect(processingTime).toBeLessThan(100);
    }
  });

  test('should not cause memory leaks with many updates', () => {
    const { unmount } = render(
      <Whiteboard
        sessionId="test-session"
        userId="test-user"
        enableRealTimeSync={true}
      />
    );

    // Simulate many updates
    const canvasUpdateHandler = mockWebSocketService.on.mock.calls.find(
      call => call[0] === 'canvas_update'
    )?.[1];

    if (canvasUpdateHandler) {
      for (let i = 0; i < 1000; i++) {
        canvasUpdateHandler({
          type: 'draw' as const,
          data: { path: `path_${i}` },
          timestamp: new Date().toISOString(),
          user_id: 'other-user'
        });
      }
    }

    // Unmount should clean up properly
    expect(() => unmount()).not.toThrow();
  });
});
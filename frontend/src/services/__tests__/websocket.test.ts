/**
 * Tests for WebSocket service
 */
import { webSocketService, CanvasUpdate, ConnectionStatus } from '../websocket';
import { io } from 'socket.io-client';

// Mock socket.io-client
jest.mock('socket.io-client');
const mockIo = io as jest.MockedFunction<typeof io>;

describe('WebSocketService', () => {
  let mockSocket: any;

  beforeEach(() => {
    // Reset the service
    webSocketService.disconnect();
    
    // Create mock socket
    mockSocket = {
      on: jest.fn(),
      off: jest.fn(),
      emit: jest.fn(),
      connect: jest.fn(),
      disconnect: jest.fn(),
      connected: false
    };

    mockIo.mockReturnValue(mockSocket);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Connection Management', () => {
    test('should connect to WebSocket server', async () => {
      const connectPromise = webSocketService.connect('http://localhost:8000');
      
      // Simulate successful connection
      const connectCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
      connectCallback();
      
      await expect(connectPromise).resolves.toBeUndefined();
      expect(mockIo).toHaveBeenCalledWith('http://localhost:8000', expect.any(Object));
    });

    test('should handle connection errors', async () => {
      const connectPromise = webSocketService.connect('http://localhost:8000');
      
      // Simulate connection error
      const errorCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect_error')[1];
      errorCallback(new Error('Connection failed'));
      
      await expect(connectPromise).rejects.toThrow('Connection failed');
    });

    test('should disconnect from server', () => {
      webSocketService.disconnect();
      expect(mockSocket.disconnect).toHaveBeenCalled();
    });

    test('should report connection status correctly', () => {
      expect(webSocketService.isSocketConnected()).toBe(false);
      
      // Simulate connection
      mockSocket.connected = true;
      // Note: In real implementation, this would be updated by connection events
    });
  });

  describe('Session Management', () => {
    beforeEach(async () => {
      // Setup connected state
      const connectPromise = webSocketService.connect();
      const connectCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
      connectCallback();
      await connectPromise;
    });

    test('should join a session', async () => {
      mockSocket.emit.mockImplementation((event, data, callback) => {
        if (callback) callback({ success: true });
      });

      await webSocketService.joinSession('session123', 'user456');
      
      expect(mockSocket.emit).toHaveBeenCalledWith(
        'join_session',
        { session_id: 'session123', user_id: 'user456' },
        expect.any(Function)
      );
    });

    test('should leave a session', async () => {
      // First join a session
      await webSocketService.joinSession('session123', 'user456');
      
      mockSocket.emit.mockImplementation((event, data, callback) => {
        if (callback) callback({ success: true });
      });

      await webSocketService.leaveSession();
      
      expect(mockSocket.emit).toHaveBeenCalledWith(
        'leave_session',
        { session_id: 'session123' },
        expect.any(Function)
      );
    });
  });

  describe('Canvas Synchronization', () => {
    beforeEach(async () => {
      // Setup connected state and session
      const connectPromise = webSocketService.connect();
      const connectCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
      connectCallback();
      await connectPromise;
      await webSocketService.joinSession('session123', 'user456');
    });

    test('should send canvas updates', () => {
      const canvasUpdate: CanvasUpdate = {
        type: 'draw',
        data: { path: 'test_path', color: 'red' },
        timestamp: new Date().toISOString()
      };

      webSocketService.sendCanvasUpdate(canvasUpdate);

      expect(mockSocket.emit).toHaveBeenCalledWith(
        'canvas_update',
        expect.objectContaining({
          type: 'draw',
          data: { path: 'test_path', color: 'red' },
          timestamp: expect.any(String)
        }),
        expect.any(Function)
      );
    });

    test('should handle incoming canvas updates', () => {
      const mockCallback = jest.fn();
      webSocketService.on('canvas_update', mockCallback);

      // Simulate incoming canvas update
      const canvasUpdateCallback = mockSocket.on.mock.calls.find(
        call => call[0] === 'canvas_update'
      )[1];
      
      const incomingUpdate = {
        type: 'draw',
        data: { path: 'remote_path' },
        user_id: 'other_user',
        timestamp: new Date().toISOString()
      };

      canvasUpdateCallback(incomingUpdate);

      expect(mockCallback).toHaveBeenCalledWith(incomingUpdate);
    });
  });

  describe('Message Queuing', () => {
    test('should queue messages when disconnected', () => {
      // Don't connect, so messages should be queued
      const canvasUpdate: CanvasUpdate = {
        type: 'draw',
        data: { path: 'test_path' },
        timestamp: new Date().toISOString()
      };

      // This should not throw and should queue the message
      expect(() => {
        webSocketService.sendCanvasUpdate(canvasUpdate);
      }).not.toThrow();

      // Socket emit should not be called when disconnected
      expect(mockSocket.emit).not.toHaveBeenCalled();
    });

    test('should process queued messages on reconnection', async () => {
      // Send message while disconnected (should be queued)
      const canvasUpdate: CanvasUpdate = {
        type: 'draw',
        data: { path: 'queued_path' },
        timestamp: new Date().toISOString()
      };

      webSocketService.sendCanvasUpdate(canvasUpdate);

      // Now connect
      const connectPromise = webSocketService.connect();
      const connectCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
      connectCallback();
      await connectPromise;

      // Join session to enable message sending
      await webSocketService.joinSession('session123', 'user456');

      // Wait a bit for queue processing
      await new Promise(resolve => setTimeout(resolve, 100));

      // Should have processed the queued message
      expect(mockSocket.emit).toHaveBeenCalledWith(
        'canvas_update',
        expect.objectContaining({
          type: 'draw',
          data: { path: 'queued_path' }
        }),
        expect.any(Function)
      );
    });
  });

  describe('Connection Status Monitoring', () => {
    test('should notify connection status changes', async () => {
      const statusCallback = jest.fn();
      webSocketService.onConnectionStatusChange(statusCallback);

      // Connect
      const connectPromise = webSocketService.connect();
      const connectCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
      connectCallback();
      await connectPromise;

      expect(statusCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          isConnected: true,
          reconnectAttempts: 0,
          networkStatus: 'online'
        })
      );
    });

    test('should handle network status changes', () => {
      const networkCallback = jest.fn();
      webSocketService.onNetworkStatusChange(networkCallback);

      // Simulate network going offline
      const offlineEvent = new Event('offline');
      window.dispatchEvent(offlineEvent);

      expect(networkCallback).toHaveBeenCalledWith(false);

      // Simulate network coming back online
      const onlineEvent = new Event('online');
      window.dispatchEvent(onlineEvent);

      expect(networkCallback).toHaveBeenCalledWith(true);
    });
  });

  describe('Audio Processing', () => {
    beforeEach(async () => {
      // Setup connected state and session
      const connectPromise = webSocketService.connect();
      const connectCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
      connectCallback();
      await connectPromise;
      await webSocketService.joinSession('session123', 'user456');
    });

    test('should send audio chunks', () => {
      const audioChunk = {
        data: new ArrayBuffer(1024),
        timestamp: new Date().toISOString(),
        sequence: 1
      };

      webSocketService.sendAudioChunk(audioChunk);

      expect(mockSocket.emit).toHaveBeenCalledWith(
        'audio_chunk',
        audioChunk,
        expect.any(Function)
      );
    });

    test('should handle audio acknowledgments', () => {
      const mockCallback = jest.fn();
      webSocketService.on('audio_received', mockCallback);

      // Simulate audio acknowledgment
      const audioReceivedCallback = mockSocket.on.mock.calls.find(
        call => call[0] === 'audio_received'
      )[1];
      
      audioReceivedCallback({ status: 'received' });

      expect(mockCallback).toHaveBeenCalledWith({ status: 'received' });
    });
  });

  describe('Error Handling', () => {
    test('should handle WebSocket errors', () => {
      const mockCallback = jest.fn();
      webSocketService.on('error', mockCallback);

      // Simulate WebSocket error
      const errorCallback = mockSocket.on.mock.calls.find(call => call[0] === 'error')[1];
      const error = { message: 'WebSocket error', code: 1001 };
      
      errorCallback(error);

      expect(mockCallback).toHaveBeenCalledWith(error);
    });

    test('should handle disconnection and attempt reconnection', () => {
      // Mock setTimeout to control reconnection timing
      jest.useFakeTimers();

      // Simulate disconnection
      const disconnectCallback = mockSocket.on.mock.calls.find(
        call => call[0] === 'disconnect'
      )[1];
      
      disconnectCallback('transport close');

      // Should attempt reconnection
      expect(setTimeout).toHaveBeenCalled();

      // Fast-forward time to trigger reconnection
      jest.advanceTimersByTime(2000);

      expect(mockSocket.connect).toHaveBeenCalled();

      jest.useRealTimers();
    });
  });

  describe('Cleanup', () => {
    test('should cleanup resources properly', () => {
      const statusCallback = jest.fn();
      webSocketService.onConnectionStatusChange(statusCallback);

      webSocketService.cleanup();

      // Should disconnect and clear callbacks
      expect(mockSocket.disconnect).toHaveBeenCalled();
    });
  });
});

describe('WebSocketService Integration', () => {
  test('should handle multiple concurrent operations', async () => {
    const mockSocket = {
      on: jest.fn(),
      off: jest.fn(),
      emit: jest.fn((event, data, callback) => {
        if (callback) setTimeout(() => callback({ success: true }), 10);
      }),
      connect: jest.fn(),
      disconnect: jest.fn(),
      connected: true
    };

    mockIo.mockReturnValue(mockSocket);

    // Connect
    const connectPromise = webSocketService.connect();
    const connectCallback = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
    connectCallback();
    await connectPromise;

    // Join session
    await webSocketService.joinSession('session123', 'user456');

    // Send multiple operations concurrently
    const operations = [
      webSocketService.sendCanvasUpdate({
        type: 'draw',
        data: { path: 'path1' },
        timestamp: new Date().toISOString()
      }),
      webSocketService.sendCanvasUpdate({
        type: 'draw',
        data: { path: 'path2' },
        timestamp: new Date().toISOString()
      }),
      webSocketService.sendChatMessage({
        message: 'Hello',
        message_id: 'msg1',
        timestamp: new Date().toISOString()
      })
    ];

    // All operations should complete successfully
    await expect(Promise.all(operations)).resolves.toBeDefined();

    // Should have made multiple emit calls
    expect(mockSocket.emit).toHaveBeenCalledTimes(5); // connect, join, 3 operations
  });
});
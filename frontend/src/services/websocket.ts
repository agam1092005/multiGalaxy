/**
 * WebSocket service for real-time communication with backend
 */
import { io, Socket } from 'socket.io-client';

export interface CanvasUpdate {
  type: 'draw' | 'erase' | 'clear' | 'object_added' | 'object_modified' | 'object_removed';
  data: any;
  timestamp: string;
  user_id?: string;
}

export interface AudioChunk {
  data: ArrayBuffer | Blob;
  timestamp: string;
  sequence: number;
}

export interface ChatMessage {
  message: string;
  message_id: string;
  timestamp: string;
  user_id?: string;
}

export interface UserCursor {
  x: number;
  y: number;
  user_id?: string;
}

export interface SessionState {
  session_id: string;
  active_users: string[];
  canvas_updates: CanvasUpdate[];
  timestamp: string;
}

export type WebSocketEventCallback = (data: any) => void;

export interface ConnectionStatus {
  isConnected: boolean;
  reconnectAttempts: number;
  lastError?: string;
  networkStatus: 'online' | 'offline' | 'unstable';
}

class WebSocketService {
  private socket: Socket | null = null;
  private sessionId: string | null = null;
  private userId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageQueue: Array<{ event: string; data: any; timestamp: number; retries: number }> = [];
  private isConnected = false;
  private connectionStatusCallbacks: Array<(status: ConnectionStatus) => void> = [];
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private lastHeartbeat: number = 0;
  private networkStatusCallbacks: Array<(isOnline: boolean) => void> = [];

  constructor() {
    this.setupEventListeners();
    this.setupNetworkMonitoring();
    this.startMessageQueueProcessor();
  }

  /**
   * Connect to WebSocket server
   */
  connect(serverUrl: string = 'http://localhost:8000', token?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const auth = token ? { token } : undefined;
        
        this.socket = io(serverUrl, {
          auth,
          transports: ['websocket', 'polling'],
          timeout: 10000,
          forceNew: true
        });

        this.socket.on('connect', () => {
          console.log('Connected to WebSocket server');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          
          // Process queued messages
          this.processMessageQueue();
          
          resolve();
        });

        this.socket.on('connect_error', (error) => {
          console.error('WebSocket connection error:', error);
          this.isConnected = false;
          reject(error);
        });

        this.socket.on('disconnect', (reason) => {
          console.log('Disconnected from WebSocket server:', reason);
          this.isConnected = false;
          
          // Attempt reconnection for certain disconnect reasons
          if (reason === 'io server disconnect') {
            // Server initiated disconnect, don't reconnect
            return;
          }
          
          this.attemptReconnection();
        });

        this.setupEventListeners();
        
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
      this.sessionId = null;
      this.userId = null;
    }
  }

  /**
   * Join a learning session
   */
  async joinSession(sessionId: string, userId: string): Promise<void> {
    this.sessionId = sessionId;
    this.userId = userId;
    
    return this.emit('join_session', {
      session_id: sessionId,
      user_id: userId
    });
  }

  /**
   * Leave current session
   */
  async leaveSession(): Promise<void> {
    if (this.sessionId) {
      await this.emit('leave_session', {
        session_id: this.sessionId
      });
      this.sessionId = null;
    }
  }

  /**
   * Send canvas update for real-time synchronization
   */
  sendCanvasUpdate(update: CanvasUpdate): void {
    this.emit('canvas_update', {
      ...update,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Send audio chunk for processing
   */
  sendAudioChunk(audioChunk: AudioChunk): void {
    this.emit('audio_chunk', audioChunk);
  }

  /**
   * Send chat message
   */
  sendChatMessage(message: ChatMessage): void {
    this.emit('chat_message', message);
  }

  /**
   * Send user cursor position
   */
  sendCursorUpdate(cursor: UserCursor): void {
    this.emit('user_cursor', cursor);
  }

  /**
   * Register event listener
   */
  on(event: string, callback: WebSocketEventCallback): void {
    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  /**
   * Remove event listener
   */
  off(event: string, callback?: WebSocketEventCallback): void {
    if (this.socket) {
      if (callback) {
        this.socket.off(event, callback);
      } else {
        this.socket.off(event);
      }
    }
  }

  /**
   * Emit event to server with queuing for offline scenarios
   */
  private emit(event: string, data: any): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket && this.isConnected) {
        this.socket.emit(event, data, (response: any) => {
          if (response && response.error) {
            reject(new Error(response.error));
          } else {
            resolve();
          }
        });
      } else {
        // Queue message for when connection is restored
        this.messageQueue.push({ event, data });
        console.warn(`WebSocket not connected. Queued message: ${event}`);
        resolve(); // Resolve to prevent blocking UI
      }
    });
  }

  /**
   * Process queued messages when connection is restored
   */
  private processMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const { event, data } = this.messageQueue.shift()!;
      this.emit(event, data).catch(error => {
        console.error(`Failed to send queued message ${event}:`, error);
      });
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnection(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      if (this.socket) {
        this.socket.connect();
      }
    }, delay);
  }

  /**
   * Set up event listeners for incoming messages
   */
  private setupEventListeners(): void {
    if (!this.socket) return;

    // Canvas synchronization events
    this.socket.on('canvas_update', (data: CanvasUpdate) => {
      // Event will be handled by components that register listeners
    });

    // Session management events
    this.socket.on('session_join', (data: any) => {
      console.log('User joined session:', data);
    });

    this.socket.on('session_leave', (data: any) => {
      console.log('User left session:', data);
    });

    this.socket.on('session_state', (data: SessionState) => {
      console.log('Received session state:', data);
    });

    // AI response events
    this.socket.on('ai_response', (data: any) => {
      console.log('Received AI response:', data);
    });

    // Audio processing events
    this.socket.on('audio_received', (data: any) => {
      console.log('Audio chunk received by server:', data);
    });

    // Chat events
    this.socket.on('chat_message', (data: ChatMessage) => {
      console.log('Received chat message:', data);
    });

    // Cursor events
    this.socket.on('user_cursor', (data: UserCursor) => {
      // Handle cursor updates from other users
    });

    // Error handling
    this.socket.on('error', (data: any) => {
      console.error('WebSocket error:', data);
    });

    // System messages
    this.socket.on('system_message', (data: any) => {
      console.log('System message:', data);
    });
  }

  /**
   * Get connection status
   */
  isSocketConnected(): boolean {
    return this.isConnected && this.socket?.connected === true;
  }

  /**
   * Get current session ID
   */
  getCurrentSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * Get current user ID
   */
  getCurrentUserId(): string | null {
    return this.userId;
  }

  /**
   * Register callback for connection status changes
   */
  onConnectionStatusChange(callback: (status: ConnectionStatus) => void): void {
    this.connectionStatusCallbacks.push(callback);
  }

  /**
   * Register callback for network status changes
   */
  onNetworkStatusChange(callback: (isOnline: boolean) => void): void {
    this.networkStatusCallbacks.push(callback);
  }

  /**
   * Remove connection status callback
   */
  removeConnectionStatusCallback(callback: (status: ConnectionStatus) => void): void {
    const index = this.connectionStatusCallbacks.indexOf(callback);
    if (index > -1) {
      this.connectionStatusCallbacks.splice(index, 1);
    }
  }

  /**
   * Setup network monitoring
   */
  private setupNetworkMonitoring(): void {
    // Monitor online/offline status
    window.addEventListener('online', () => {
      console.log('Network came back online');
      this.notifyNetworkStatus(true);
      
      // Attempt to reconnect if disconnected
      if (!this.isConnected && this.socket) {
        this.attemptReconnection();
      }
    });

    window.addEventListener('offline', () => {
      console.log('Network went offline');
      this.notifyNetworkStatus(false);
      this.notifyConnectionStatus();
    });

    // Check initial network status
    this.notifyNetworkStatus(navigator.onLine);
  }

  /**
   * Start heartbeat mechanism
   */
  private startHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    this.heartbeatInterval = setInterval(() => {
      if (this.socket && this.isConnected) {
        this.lastHeartbeat = Date.now();
        this.socket.emit('ping', { timestamp: this.lastHeartbeat });
      }
    }, 30000); // Send ping every 30 seconds
  }

  /**
   * Stop heartbeat mechanism
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Enhanced message queue processor with retry logic
   */
  private startMessageQueueProcessor(): void {
    setInterval(() => {
      if (this.isConnected && this.messageQueue.length > 0) {
        const now = Date.now();
        const messagesToProcess = [...this.messageQueue];
        this.messageQueue = [];

        messagesToProcess.forEach(queuedMessage => {
          // Check if message is too old (older than 5 minutes)
          if (now - queuedMessage.timestamp > 300000) {
            console.warn('Dropping old queued message:', queuedMessage.event);
            return;
          }

          // Check retry limit
          if (queuedMessage.retries >= 3) {
            console.error('Max retries reached for message:', queuedMessage.event);
            return;
          }

          // Try to send the message
          this.emit(queuedMessage.event, queuedMessage.data).catch(error => {
            console.error(`Failed to send queued message ${queuedMessage.event}:`, error);
            
            // Re-queue with incremented retry count
            this.messageQueue.push({
              ...queuedMessage,
              retries: queuedMessage.retries + 1
            });
          });
        });
      }
    }, 5000); // Process queue every 5 seconds
  }

  /**
   * Enhanced emit with better error handling and queuing
   */
  private emit(event: string, data: any): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket && this.isConnected) {
        // Add timeout for acknowledgment
        const timeout = setTimeout(() => {
          reject(new Error(`Timeout waiting for acknowledgment of ${event}`));
        }, 10000);

        this.socket.emit(event, data, (response: any) => {
          clearTimeout(timeout);
          
          if (response && response.error) {
            reject(new Error(response.error));
          } else {
            resolve();
          }
        });
      } else {
        // Queue message for when connection is restored
        this.messageQueue.push({ 
          event, 
          data, 
          timestamp: Date.now(),
          retries: 0
        });
        
        console.warn(`WebSocket not connected. Queued message: ${event}`);
        resolve(); // Resolve to prevent blocking UI
      }
    });
  }

  /**
   * Enhanced reconnection with exponential backoff and jitter
   */
  private attemptReconnection(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.notifyConnectionStatus('Max reconnection attempts reached');
      return;
    }

    // Don't attempt reconnection if offline
    if (!navigator.onLine) {
      console.log('Skipping reconnection attempt - network is offline');
      return;
    }

    this.reconnectAttempts++;
    
    // Exponential backoff with jitter
    const baseDelay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    const delay = Math.min(baseDelay + jitter, 30000); // Cap at 30 seconds
    
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${Math.round(delay)}ms`);
    
    this.notifyConnectionStatus();

    setTimeout(() => {
      if (this.socket && !this.isConnected) {
        this.socket.connect();
      }
    }, delay);
  }

  /**
   * Notify connection status callbacks
   */
  private notifyConnectionStatus(error?: string): void {
    const status: ConnectionStatus = {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      lastError: error,
      networkStatus: navigator.onLine ? 
        (this.isConnected ? 'online' : 'unstable') : 'offline'
    };

    this.connectionStatusCallbacks.forEach(callback => {
      try {
        callback(status);
      } catch (err) {
        console.error('Error in connection status callback:', err);
      }
    });
  }

  /**
   * Notify network status callbacks
   */
  private notifyNetworkStatus(isOnline: boolean): void {
    this.networkStatusCallbacks.forEach(callback => {
      try {
        callback(isOnline);
      } catch (err) {
        console.error('Error in network status callback:', err);
      }
    });
  }

  /**
   * Enhanced setup with better error handling
   */
  private setupEventListeners(): void {
    if (!this.socket) return;

    // Connection events with enhanced handling
    this.socket.on('connect', () => {
      console.log('Connected to WebSocket server');
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.notifyConnectionStatus();
      
      // Process queued messages
      this.processMessageQueue();
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.isConnected = false;
      this.stopHeartbeat();
      this.notifyConnectionStatus(error.message);
    });

    this.socket.on('disconnect', (reason) => {
      console.log('Disconnected from WebSocket server:', reason);
      this.isConnected = false;
      this.stopHeartbeat();
      this.notifyConnectionStatus(reason);
      
      // Attempt reconnection for certain disconnect reasons
      if (reason === 'io server disconnect') {
        // Server initiated disconnect, don't reconnect immediately
        setTimeout(() => this.attemptReconnection(), 5000);
      } else {
        this.attemptReconnection();
      }
    });

    // Heartbeat response
    this.socket.on('pong', (data: any) => {
      const latency = Date.now() - data.timestamp;
      console.log(`Heartbeat latency: ${latency}ms`);
    });

    // Enhanced error handling
    this.socket.on('error', (error: any) => {
      console.error('WebSocket error:', error);
      this.notifyConnectionStatus(error.message || 'Unknown error');
    });

    // Connection quality monitoring
    this.socket.on('reconnect', (attemptNumber: number) => {
      console.log(`Reconnected after ${attemptNumber} attempts`);
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.notifyConnectionStatus();
    });

    this.socket.on('reconnect_error', (error: any) => {
      console.error('Reconnection error:', error);
      this.notifyConnectionStatus(error.message);
    });

    this.socket.on('reconnect_failed', () => {
      console.error('Reconnection failed after all attempts');
      this.notifyConnectionStatus('Reconnection failed');
    });
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.stopHeartbeat();
    this.connectionStatusCallbacks = [];
    this.networkStatusCallbacks = [];
    this.messageQueue = [];
    this.disconnect();
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();
export default webSocketService;
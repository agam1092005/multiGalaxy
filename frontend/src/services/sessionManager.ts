/**
 * Session management service for handling learning sessions
 */
import { webSocketService, SessionState } from './websocket';

export interface LearningSession {
  id: string;
  userId: string;
  subject: string;
  startTime: Date;
  endTime?: Date;
  participants: string[];
  canvasState?: any;
  isActive: boolean;
}

export interface SessionParticipant {
  userId: string;
  username: string;
  role: 'student' | 'teacher' | 'parent';
  joinedAt: Date;
  isActive: boolean;
}

class SessionManager {
  private currentSession: LearningSession | null = null;
  private participants: Map<string, SessionParticipant> = new Map();
  private sessionStateCallbacks: Array<(state: SessionState) => void> = [];
  private participantCallbacks: Array<(participants: SessionParticipant[]) => void> = [];

  constructor() {
    this.setupWebSocketListeners();
  }

  /**
   * Create a new learning session
   */
  async createSession(userId: string, subject: string): Promise<LearningSession> {
    const session: LearningSession = {
      id: this.generateSessionId(),
      userId,
      subject,
      startTime: new Date(),
      participants: [userId],
      isActive: true
    };

    this.currentSession = session;
    
    // Connect to WebSocket if not already connected
    if (!webSocketService.isSocketConnected()) {
      await webSocketService.connect();
    }

    // Join the session
    await webSocketService.joinSession(session.id, userId);

    return session;
  }

  /**
   * Join an existing session
   */
  async joinSession(sessionId: string, userId: string, username: string, role: 'student' | 'teacher' | 'parent' = 'student'): Promise<void> {
    // Connect to WebSocket if not already connected
    if (!webSocketService.isSocketConnected()) {
      await webSocketService.connect();
    }

    // Join the session via WebSocket
    await webSocketService.joinSession(sessionId, userId);

    // Update local session state
    if (this.currentSession && this.currentSession.id === sessionId) {
      if (!this.currentSession.participants.includes(userId)) {
        this.currentSession.participants.push(userId);
      }
    } else {
      // Create session object for joined session
      this.currentSession = {
        id: sessionId,
        userId,
        subject: 'Unknown', // Will be updated when session state is received
        startTime: new Date(),
        participants: [userId],
        isActive: true
      };
    }

    // Add participant
    this.participants.set(userId, {
      userId,
      username,
      role,
      joinedAt: new Date(),
      isActive: true
    });

    this.notifyParticipantChange();
  }

  /**
   * Leave current session
   */
  async leaveSession(): Promise<void> {
    if (!this.currentSession) return;

    const sessionId = this.currentSession.id;
    const userId = this.currentSession.userId;

    // Leave via WebSocket
    await webSocketService.leaveSession();

    // Update local state
    this.currentSession.isActive = false;
    this.currentSession.endTime = new Date();

    // Remove from participants
    this.participants.delete(userId);
    this.notifyParticipantChange();

    // Clear current session
    this.currentSession = null;
  }

  /**
   * End current session (for session owner)
   */
  async endSession(): Promise<void> {
    if (!this.currentSession) return;

    // Mark session as ended
    this.currentSession.isActive = false;
    this.currentSession.endTime = new Date();

    // Leave the session
    await this.leaveSession();
  }

  /**
   * Get current session
   */
  getCurrentSession(): LearningSession | null {
    return this.currentSession;
  }

  /**
   * Get session participants
   */
  getParticipants(): SessionParticipant[] {
    return Array.from(this.participants.values());
  }

  /**
   * Check if user is in a session
   */
  isInSession(): boolean {
    return this.currentSession !== null && this.currentSession.isActive;
  }

  /**
   * Save canvas state to session
   */
  saveCanvasState(canvasState: any): void {
    if (this.currentSession) {
      this.currentSession.canvasState = canvasState;
    }
  }

  /**
   * Get saved canvas state
   */
  getCanvasState(): any {
    return this.currentSession?.canvasState;
  }

  /**
   * Register callback for session state changes
   */
  onSessionStateChange(callback: (state: SessionState) => void): void {
    this.sessionStateCallbacks.push(callback);
  }

  /**
   * Register callback for participant changes
   */
  onParticipantChange(callback: (participants: SessionParticipant[]) => void): void {
    this.participantCallbacks.push(callback);
  }

  /**
   * Remove callback
   */
  removeCallback(callback: Function): void {
    const stateIndex = this.sessionStateCallbacks.indexOf(callback as any);
    if (stateIndex > -1) {
      this.sessionStateCallbacks.splice(stateIndex, 1);
    }

    const participantIndex = this.participantCallbacks.indexOf(callback as any);
    if (participantIndex > -1) {
      this.participantCallbacks.splice(participantIndex, 1);
    }
  }

  /**
   * Setup WebSocket event listeners
   */
  private setupWebSocketListeners(): void {
    // Handle session state updates
    webSocketService.on('session_state', (state: SessionState) => {
      if (this.currentSession && this.currentSession.id === state.session_id) {
        // Update participants list
        state.active_users.forEach(userId => {
          if (!this.participants.has(userId)) {
            this.participants.set(userId, {
              userId,
              username: `User ${userId}`, // Placeholder, should be fetched from user service
              role: 'student',
              joinedAt: new Date(),
              isActive: true
            });
          }
        });

        // Remove inactive participants
        this.participants.forEach((participant, userId) => {
          if (!state.active_users.includes(userId)) {
            this.participants.delete(userId);
          }
        });

        this.notifyParticipantChange();
      }

      // Notify session state callbacks
      this.sessionStateCallbacks.forEach(callback => callback(state));
    });

    // Handle user joining
    webSocketService.on('session_join', (data: any) => {
      if (this.currentSession && this.currentSession.id === data.session_id) {
        const userId = data.user_id;
        
        if (!this.participants.has(userId)) {
          this.participants.set(userId, {
            userId,
            username: `User ${userId}`,
            role: 'student',
            joinedAt: new Date(data.timestamp),
            isActive: true
          });
          
          this.notifyParticipantChange();
        }
      }
    });

    // Handle user leaving
    webSocketService.on('session_leave', (data: any) => {
      if (this.currentSession && this.currentSession.id === data.session_id) {
        const userId = data.user_id;
        this.participants.delete(userId);
        this.notifyParticipantChange();
      }
    });

    // Handle connection errors
    webSocketService.on('error', (error: any) => {
      console.error('Session WebSocket error:', error);
      // Could implement retry logic or user notification here
    });
  }

  /**
   * Notify all participant change callbacks
   */
  private notifyParticipantChange(): void {
    const participants = this.getParticipants();
    this.participantCallbacks.forEach(callback => callback(participants));
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.sessionStateCallbacks = [];
    this.participantCallbacks = [];
    this.participants.clear();
    this.currentSession = null;
  }
}

// Export singleton instance
export const sessionManager = new SessionManager();
export default sessionManager;
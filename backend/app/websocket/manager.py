"""
WebSocket connection manager for real-time communication
"""
import socketio
import asyncio
import json
import logging
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import redis
from app.core.config import get_settings
from app.services.message_queue import message_queue, MessagePriority
from app.services.audio_processor import audio_processor

settings = get_settings()
logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    CANVAS_UPDATE = "canvas_update"
    AUDIO_CHUNK = "audio_chunk"
    AUDIO_STREAM_START = "audio_stream_start"
    AUDIO_STREAM_STOP = "audio_stream_stop"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    AUDIO_QUALITY_UPDATE = "audio_quality_update"
    CHAT_MESSAGE = "chat_message"
    SESSION_JOIN = "session_join"
    SESSION_LEAVE = "session_leave"
    USER_CURSOR = "user_cursor"
    SYSTEM_MESSAGE = "system_message"
    ERROR = "error"

class ConnectionManager:
    def __init__(self):
        # Create Socket.IO server with Redis adapter for scaling
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",
            async_mode='asgi',
            logger=True,
            engineio_logger=True
        )
        
        # Redis client for message queuing and session management
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True
        )
        
        # In-memory storage for active sessions and connections
        self.active_sessions: Dict[str, Dict] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.session_users: Dict[str, List[str]] = {}  # session_id -> [user_ids]
        
        # Audio streaming state
        self.active_audio_streams: Dict[str, Dict] = {}  # sid -> stream_info
        
        # Message queue for reliable delivery
        self.message_queue: Dict[str, List[Dict]] = {}
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Set up Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection"""
            logger.info(f"Client {sid} connected")
            
            # Authenticate user if auth token provided
            user_id = None
            if auth and 'token' in auth:
                user_id = await self._authenticate_user(auth['token'])
                if not user_id:
                    await self.sio.disconnect(sid)
                    return False
            
            # Store connection info
            await self.sio.save_session(sid, {
                'user_id': user_id,
                'connected_at': datetime.utcnow().isoformat(),
                'session_id': None
            })
            
            return True
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            logger.info(f"Client {sid} disconnected")
            
            session_data = await self.sio.get_session(sid)
            if session_data and session_data.get('session_id'):
                await self._leave_session(sid, session_data['session_id'])
        
        @self.sio.event
        async def join_session(sid, data):
            """Handle user joining a learning session"""
            try:
                session_id = data.get('session_id')
                user_id = data.get('user_id')
                
                if not session_id or not user_id:
                    await self._send_error(sid, "Missing session_id or user_id")
                    return
                
                await self._join_session(sid, session_id, user_id)
                
            except Exception as e:
                logger.error(f"Error joining session: {e}")
                await self._send_error(sid, "Failed to join session")
        
        @self.sio.event
        async def leave_session(sid, data):
            """Handle user leaving a learning session"""
            try:
                session_id = data.get('session_id')
                await self._leave_session(sid, session_id)
                
            except Exception as e:
                logger.error(f"Error leaving session: {e}")
                await self._send_error(sid, "Failed to leave session")
        
        @self.sio.event
        async def canvas_update(sid, data):
            """Handle canvas updates for real-time synchronization"""
            try:
                await self._handle_canvas_update(sid, data)
            except Exception as e:
                logger.error(f"Error handling canvas update: {e}")
                await self._send_error(sid, "Failed to process canvas update")
        
        @self.sio.event
        async def audio_chunk(sid, data):
            """Handle audio chunks for real-time processing"""
            try:
                await self._handle_audio_chunk(sid, data)
            except Exception as e:
                logger.error(f"Error handling audio chunk: {e}")
                await self._send_error(sid, "Failed to process audio")
        
        @self.sio.event
        async def start_audio_stream(sid, data):
            """Handle audio stream initialization"""
            try:
                await self._start_audio_stream(sid, data)
            except Exception as e:
                logger.error(f"Error starting audio stream: {e}")
                await self._send_error(sid, "Failed to start audio stream")
        
        @self.sio.event
        async def stop_audio_stream(sid, data):
            """Handle audio stream termination"""
            try:
                await self._stop_audio_stream(sid, data)
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
                await self._send_error(sid, "Failed to stop audio stream")
        
        @self.sio.event
        async def chat_message(sid, data):
            """Handle chat messages"""
            try:
                await self._handle_chat_message(sid, data)
            except Exception as e:
                logger.error(f"Error handling chat message: {e}")
                await self._send_error(sid, "Failed to send message")
        
        @self.sio.event
        async def user_cursor(sid, data):
            """Handle user cursor position updates"""
            try:
                await self._handle_cursor_update(sid, data)
            except Exception as e:
                logger.error(f"Error handling cursor update: {e}")
    
    async def _authenticate_user(self, token: str) -> Optional[str]:
        """Authenticate user token and return user_id"""
        # TODO: Implement JWT token validation
        # For now, return a mock user_id
        return "user_123"
    
    async def _join_session(self, sid: str, session_id: str, user_id: str):
        """Add user to a learning session"""
        # Update session data
        session_data = await self.sio.get_session(sid)
        session_data['session_id'] = session_id
        session_data['user_id'] = user_id
        await self.sio.save_session(sid, session_data)
        
        # Join Socket.IO room
        await self.sio.enter_room(sid, session_id)
        
        # Update session tracking
        if session_id not in self.session_users:
            self.session_users[session_id] = []
        
        if user_id not in self.session_users[session_id]:
            self.session_users[session_id].append(user_id)
        
        self.user_sessions[user_id] = session_id
        
        # Store session info in Redis for persistence
        await self._store_session_info(session_id, user_id, 'joined')
        
        # Notify other users in the session
        await self.sio.emit(
            MessageType.SESSION_JOIN,
            {
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=session_id,
            skip_sid=sid
        )
        
        # Send session state to the joining user
        session_state = await self._get_session_state(session_id)
        await self.sio.emit(
            'session_state',
            session_state,
            room=sid
        )
        
        logger.info(f"User {user_id} joined session {session_id}")
    
    async def _leave_session(self, sid: str, session_id: str):
        """Remove user from a learning session"""
        session_data = await self.sio.get_session(sid)
        user_id = session_data.get('user_id')
        
        if not session_id or not user_id:
            return
        
        # Leave Socket.IO room
        await self.sio.leave_room(sid, session_id)
        
        # Update session tracking
        if session_id in self.session_users and user_id in self.session_users[session_id]:
            self.session_users[session_id].remove(user_id)
            
            if not self.session_users[session_id]:
                del self.session_users[session_id]
        
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        # Store session info in Redis
        await self._store_session_info(session_id, user_id, 'left')
        
        # Notify other users in the session
        await self.sio.emit(
            MessageType.SESSION_LEAVE,
            {
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=session_id
        )
        
        logger.info(f"User {user_id} left session {session_id}")
    
    async def _handle_canvas_update(self, sid: str, data: Dict[str, Any]):
        """Handle real-time canvas synchronization"""
        session_data = await self.sio.get_session(sid)
        session_id = session_data.get('session_id')
        user_id = session_data.get('user_id')
        
        if not session_id:
            await self._send_error(sid, "Not in a session")
            return
        
        # Add metadata to canvas update
        canvas_update = {
            'type': MessageType.CANVAS_UPDATE,
            'user_id': user_id,
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        # Store in Redis for persistence and recovery
        await self._queue_message(session_id, canvas_update)
        
        # Broadcast to other users in the session
        await self.sio.emit(
            MessageType.CANVAS_UPDATE,
            canvas_update,
            room=session_id,
            skip_sid=sid
        )
    
    async def _start_audio_stream(self, sid: str, data: Dict[str, Any]):
        """Initialize audio streaming for a user"""
        session_data = await self.sio.get_session(sid)
        session_id = session_data.get('session_id')
        user_id = session_data.get('user_id')
        
        if not session_id:
            await self._send_error(sid, "Not in a session")
            return
        
        # Store audio stream info
        self.active_audio_streams[sid] = {
            'user_id': user_id,
            'session_id': session_id,
            'started_at': datetime.utcnow(),
            'sample_rate': data.get('sample_rate', 16000),
            'channels': data.get('channels', 1),
            'chunk_count': 0
        }
        
        # Validate audio processor setup
        validation = await audio_processor.validate_audio_setup()
        
        if not validation['is_ready']:
            await self._send_error(sid, f"Audio processing not ready: {validation['errors']}")
            return
        
        # Acknowledge stream start
        await self.sio.emit('audio_stream_started', {
            'status': 'started',
            'session_id': session_id,
            'audio_config': {
                'sample_rate': self.active_audio_streams[sid]['sample_rate'],
                'channels': self.active_audio_streams[sid]['channels']
            }
        }, room=sid)
        
        logger.info(f"Audio stream started for user {user_id} in session {session_id}")
    
    async def _stop_audio_stream(self, sid: str, data: Dict[str, Any]):
        """Stop audio streaming for a user"""
        if sid in self.active_audio_streams:
            stream_info = self.active_audio_streams[sid]
            duration = (datetime.utcnow() - stream_info['started_at']).total_seconds()
            
            # Clean up stream
            del self.active_audio_streams[sid]
            
            # Send stream summary
            await self.sio.emit('audio_stream_stopped', {
                'status': 'stopped',
                'duration_seconds': duration,
                'chunks_processed': stream_info['chunk_count']
            }, room=sid)
            
            logger.info(f"Audio stream stopped for user {stream_info['user_id']}")
    
    async def _handle_audio_chunk(self, sid: str, data: Dict[str, Any]):
        """Handle audio chunks for real-time processing"""
        session_data = await self.sio.get_session(sid)
        session_id = session_data.get('session_id')
        user_id = session_data.get('user_id')
        
        if not session_id:
            await self._send_error(sid, "Not in a session")
            return
        
        if sid not in self.active_audio_streams:
            await self._send_error(sid, "Audio stream not started")
            return
        
        try:
            # Decode base64 audio data
            audio_data_b64 = data.get('audio_data')
            if not audio_data_b64:
                await self._send_error(sid, "No audio data provided")
                return
            
            audio_bytes = base64.b64decode(audio_data_b64)
            
            # Process audio chunk
            processing_result = await audio_processor.process_audio_chunk(
                audio_bytes, session_id, user_id
            )
            
            # Update chunk count
            self.active_audio_streams[sid]['chunk_count'] += 1
            
            # Send quality feedback to user
            if processing_result['quality']['quality_level'] == 'poor':
                await self.sio.emit(MessageType.AUDIO_QUALITY_UPDATE, {
                    'quality': processing_result['quality'],
                    'suggestion': self._get_quality_suggestion(processing_result['quality'])
                }, room=sid)
            
            # Send transcription if available
            if processing_result['transcription']:
                transcription_message = {
                    'type': MessageType.AUDIO_TRANSCRIPTION,
                    'user_id': user_id,
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'transcription': processing_result['transcription']
                }
                
                # Store transcription
                await self._queue_message(f"{session_id}:transcription", transcription_message)
                
                # Broadcast to session (for collaborative features)
                await self.sio.emit(
                    MessageType.AUDIO_TRANSCRIPTION,
                    transcription_message,
                    room=session_id
                )
            
            # Acknowledge chunk processing
            await self.sio.emit('audio_chunk_processed', {
                'status': 'processed',
                'chunk_id': data.get('chunk_id'),
                'voice_activity': processing_result['voice_activity'],
                'buffer_size': processing_result['buffer_size']
            }, room=sid)
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            await self._send_error(sid, f"Audio processing failed: {str(e)}")
    
    def _get_quality_suggestion(self, quality_metrics: Dict[str, Any]) -> str:
        """Generate quality improvement suggestions"""
        suggestions = []
        
        if quality_metrics['volume_db'] < -30:
            suggestions.append("Please speak louder or move closer to the microphone")
        elif quality_metrics['volume_db'] > -5:
            suggestions.append("Please speak softer or move away from the microphone")
        
        if quality_metrics['snr_db'] < 10:
            suggestions.append("Please reduce background noise")
        
        if quality_metrics['clipping_ratio'] > 0.1:
            suggestions.append("Audio is clipping, please reduce input volume")
        
        return "; ".join(suggestions) if suggestions else "Audio quality is acceptable"
    
    async def _handle_chat_message(self, sid: str, data: Dict[str, Any]):
        """Handle chat messages"""
        session_data = await self.sio.get_session(sid)
        session_id = session_data.get('session_id')
        user_id = session_data.get('user_id')
        
        if not session_id:
            await self._send_error(sid, "Not in a session")
            return
        
        chat_message = {
            'type': MessageType.CHAT_MESSAGE,
            'user_id': user_id,
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'message': data.get('message', ''),
            'message_id': data.get('message_id')
        }
        
        # Store message
        await self._queue_message(session_id, chat_message)
        
        # Broadcast to all users in the session
        await self.sio.emit(
            MessageType.CHAT_MESSAGE,
            chat_message,
            room=session_id
        )
    
    async def _handle_cursor_update(self, sid: str, data: Dict[str, Any]):
        """Handle user cursor position updates"""
        session_data = await self.sio.get_session(sid)
        session_id = session_data.get('session_id')
        user_id = session_data.get('user_id')
        
        if not session_id:
            return
        
        cursor_update = {
            'type': MessageType.USER_CURSOR,
            'user_id': user_id,
            'x': data.get('x'),
            'y': data.get('y'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Broadcast cursor position (no need to store)
        await self.sio.emit(
            MessageType.USER_CURSOR,
            cursor_update,
            room=session_id,
            skip_sid=sid
        )
    
    async def _send_error(self, sid: str, message: str):
        """Send error message to client"""
        await self.sio.emit(
            MessageType.ERROR,
            {
                'error': message,
                'timestamp': datetime.utcnow().isoformat()
            },
            room=sid
        )
    
    async def _queue_message(self, queue_key: str, message: Dict[str, Any]):
        """Queue message using the message queue service for reliable delivery"""
        try:
            # Determine priority based on message type
            priority = MessagePriority.NORMAL
            if message.get('type') == MessageType.SYSTEM_MESSAGE:
                priority = MessagePriority.HIGH
            elif message.get('type') == MessageType.ERROR:
                priority = MessagePriority.CRITICAL
            elif message.get('type') == MessageType.AUDIO_CHUNK:
                priority = MessagePriority.HIGH  # Audio processing is time-sensitive
            
            await message_queue.enqueue(
                queue_name=queue_key,
                payload=message,
                priority=priority,
                max_retries=3
            )
        except Exception as e:
            logger.error(f"Failed to queue message: {e}")
            # Fallback to Redis list for critical messages
            try:
                message_json = json.dumps(message)
                self.redis_client.lpush(f"fallback_queue:{queue_key}", message_json)
                self.redis_client.expire(f"fallback_queue:{queue_key}", 86400)
            except Exception as fallback_error:
                logger.error(f"Fallback queue also failed: {fallback_error}")
    
    async def _store_session_info(self, session_id: str, user_id: str, action: str):
        """Store session information in Redis"""
        try:
            session_key = f"session:{session_id}"
            session_info = {
                'user_id': user_id,
                'action': action,
                'timestamp': datetime.utcnow().isoformat()
            }
            self.redis_client.hset(session_key, user_id, json.dumps(session_info))
            self.redis_client.expire(session_key, 86400)  # 24 hours
        except Exception as e:
            logger.error(f"Failed to store session info: {e}")
    
    async def _get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current session state for new joiners"""
        try:
            # Get recent canvas updates
            canvas_messages = self.redis_client.lrange(f"queue:{session_id}", 0, 50)
            canvas_updates = []
            
            for msg in canvas_messages:
                try:
                    parsed_msg = json.loads(msg)
                    if parsed_msg.get('type') == MessageType.CANVAS_UPDATE:
                        canvas_updates.append(parsed_msg)
                except json.JSONDecodeError:
                    continue
            
            # Get active users
            active_users = self.session_users.get(session_id, [])
            
            return {
                'session_id': session_id,
                'active_users': active_users,
                'canvas_updates': canvas_updates[-10:],  # Last 10 updates
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get session state: {e}")
            return {'session_id': session_id, 'active_users': [], 'canvas_updates': []}
    
    async def send_ai_response(self, session_id: str, response_data: Dict[str, Any]):
        """Send AI response to all users in a session"""
        ai_message = {
            'type': 'ai_response',
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': response_data
        }
        
        await self.sio.emit('ai_response', ai_message, room=session_id)
    
    def get_asgi_app(self):
        """Get ASGI app for integration with FastAPI"""
        return socketio.ASGIApp(self.sio)

# Global connection manager instance
connection_manager = ConnectionManager()
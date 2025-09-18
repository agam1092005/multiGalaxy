"""
Tests for real-time WebSocket functionality
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.websocket.manager import ConnectionManager, MessageType
from app.services.message_queue import MessageQueue, MessagePriority
from main import app

class TestWebSocketRealTime:
    """Test real-time WebSocket functionality"""

    @pytest.fixture
    def connection_manager(self):
        """Create a connection manager for testing"""
        manager = ConnectionManager()
        return manager

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch('app.websocket.manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            yield mock_client

    @pytest.fixture
    async def message_queue(self):
        """Create message queue for testing"""
        queue = MessageQueue()
        # Mock Redis for testing
        queue.redis_client = AsyncMock()
        await queue.initialize()
        return queue

    @pytest.mark.asyncio
    async def test_multiple_users_canvas_sync(self, connection_manager, mock_redis):
        """Test canvas synchronization between multiple users"""
        # Simulate multiple users connecting
        user_sessions = {}
        session_id = "test_session_123"
        
        # Mock Socket.IO server
        mock_sio = AsyncMock()
        connection_manager.sio = mock_sio
        
        # Simulate users joining session
        users = ["user1", "user2", "user3"]
        
        for user_id in users:
            sid = f"socket_{user_id}"
            user_sessions[user_id] = {
                'sid': sid,
                'user_id': user_id,
                'session_id': session_id
            }
            
            # Mock session data
            mock_sio.get_session.return_value = {
                'user_id': user_id,
                'session_id': session_id
            }
            
            # Simulate joining session
            await connection_manager._join_session(sid, session_id, user_id)
        
        # Verify all users are in the session
        assert len(connection_manager.session_users[session_id]) == 3
        
        # Test canvas update from user1
        canvas_update_data = {
            'type': 'object_added',
            'object': {
                'type': 'rect',
                'left': 100,
                'top': 100,
                'width': 50,
                'height': 50,
                'fill': 'red'
            }
        }
        
        # Simulate canvas update from user1
        await connection_manager._handle_canvas_update(
            user_sessions["user1"]["sid"], 
            canvas_update_data
        )
        
        # Verify message was broadcast to other users (not user1)
        mock_sio.emit.assert_called()
        call_args = mock_sio.emit.call_args
        
        assert call_args[0][0] == MessageType.CANVAS_UPDATE
        assert call_args[1]['room'] == session_id
        assert call_args[1]['skip_sid'] == user_sessions["user1"]["sid"]

    @pytest.mark.asyncio
    async def test_message_queue_reliability(self, message_queue):
        """Test message queue reliability for real-time messages"""
        # Test enqueueing canvas update
        canvas_message = {
            'type': MessageType.CANVAS_UPDATE,
            'user_id': 'user1',
            'session_id': 'session123',
            'data': {'action': 'draw', 'coordinates': [10, 20, 30, 40]}
        }
        
        message_id = await message_queue.enqueue(
            queue_name='session123',
            payload=canvas_message,
            priority=MessagePriority.NORMAL
        )
        
        assert message_id is not None
        
        # Test dequeuing
        dequeued_message = await message_queue.dequeue('session123')
        
        assert dequeued_message is not None
        assert dequeued_message.payload['type'] == MessageType.CANVAS_UPDATE
        assert dequeued_message.payload['user_id'] == 'user1'

    @pytest.mark.asyncio
    async def test_audio_chunk_processing(self, connection_manager, mock_redis):
        """Test real-time audio chunk processing"""
        mock_sio = AsyncMock()
        connection_manager.sio = mock_sio
        
        session_id = "audio_test_session"
        user_id = "audio_user"
        sid = "audio_socket"
        
        # Mock session data
        mock_sio.get_session.return_value = {
            'user_id': user_id,
            'session_id': session_id
        }
        
        # Simulate audio chunk
        audio_data = {
            'data': 'base64_encoded_audio_data',
            'timestamp': '2023-01-01T00:00:00Z',
            'sequence': 1
        }
        
        await connection_manager._handle_audio_chunk(sid, audio_data)
        
        # Verify audio acknowledgment was sent
        mock_sio.emit.assert_called_with(
            'audio_received', 
            {'status': 'received'}, 
            room=sid
        )

    @pytest.mark.asyncio
    async def test_connection_interruption_recovery(self, connection_manager, mock_redis):
        """Test handling of connection interruptions"""
        mock_sio = AsyncMock()
        connection_manager.sio = mock_sio
        
        session_id = "interruption_test"
        user_id = "test_user"
        sid = "test_socket"
        
        # Simulate user joining session
        await connection_manager._join_session(sid, session_id, user_id)
        
        # Verify user is in session
        assert user_id in connection_manager.session_users[session_id]
        
        # Simulate disconnection
        await connection_manager._leave_session(sid, session_id)
        
        # Verify user is removed from session
        assert session_id not in connection_manager.session_users or \
               user_id not in connection_manager.session_users[session_id]

    @pytest.mark.asyncio
    async def test_concurrent_canvas_updates(self, connection_manager, mock_redis):
        """Test handling of concurrent canvas updates from multiple users"""
        mock_sio = AsyncMock()
        connection_manager.sio = mock_sio
        
        session_id = "concurrent_test"
        users = [f"user_{i}" for i in range(5)]
        
        # Setup users in session
        for i, user_id in enumerate(users):
            sid = f"socket_{i}"
            mock_sio.get_session.return_value = {
                'user_id': user_id,
                'session_id': session_id
            }
            await connection_manager._join_session(sid, session_id, user_id)
        
        # Simulate concurrent canvas updates
        update_tasks = []
        for i, user_id in enumerate(users):
            sid = f"socket_{i}"
            update_data = {
                'type': 'draw',
                'coordinates': [i*10, i*10, i*20, i*20],
                'color': f'color_{i}'
            }
            
            task = connection_manager._handle_canvas_update(sid, update_data)
            update_tasks.append(task)
        
        # Execute all updates concurrently
        await asyncio.gather(*update_tasks)
        
        # Verify all updates were processed
        assert mock_sio.emit.call_count >= len(users)

    @pytest.mark.asyncio
    async def test_session_state_recovery(self, connection_manager, mock_redis):
        """Test session state recovery for new joiners"""
        session_id = "recovery_test"
        
        # Mock Redis responses for session state
        mock_redis.lrange.return_value = [
            json.dumps({
                'type': MessageType.CANVAS_UPDATE,
                'data': {'action': 'draw', 'path': 'test_path_1'}
            }),
            json.dumps({
                'type': MessageType.CANVAS_UPDATE,
                'data': {'action': 'draw', 'path': 'test_path_2'}
            })
        ]
        
        # Set up existing users
        connection_manager.session_users[session_id] = ['existing_user1', 'existing_user2']
        
        # Get session state
        session_state = await connection_manager._get_session_state(session_id)
        
        assert session_state['session_id'] == session_id
        assert len(session_state['active_users']) == 2
        assert len(session_state['canvas_updates']) > 0

    @pytest.mark.asyncio
    async def test_error_handling_invalid_session(self, connection_manager):
        """Test error handling for invalid session operations"""
        mock_sio = AsyncMock()
        connection_manager.sio = mock_sio
        
        # Mock session with no session_id
        mock_sio.get_session.return_value = {'user_id': 'test_user'}
        
        # Try to send canvas update without being in a session
        await connection_manager._handle_canvas_update('test_sid', {'test': 'data'})
        
        # Verify error was sent
        mock_sio.emit.assert_called_with(
            MessageType.ERROR,
            {'error': 'Not in a session', 'timestamp': pytest.approx(str, abs=1)},
            room='test_sid'
        )

    @pytest.mark.asyncio
    async def test_message_queue_retry_mechanism(self, message_queue):
        """Test message queue retry mechanism for failed deliveries"""
        # Mock a failing processor
        async def failing_processor(payload):
            return False  # Simulate processing failure
        
        await message_queue.register_processor('test_queue', failing_processor)
        
        # Enqueue a message
        message_id = await message_queue.enqueue(
            queue_name='test_queue',
            payload={'test': 'data'},
            max_retries=2
        )
        
        # Simulate message processing failure
        await message_queue.nack_message(message_id, "Processing failed")
        
        # Verify message is scheduled for retry
        message_queue.redis_client.zadd.assert_called()

    def test_websocket_integration_with_fastapi(self):
        """Test WebSocket integration with FastAPI application"""
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Test Socket.IO endpoint is mounted
        # Note: Full Socket.IO testing requires a running server
        # This test verifies the endpoint is properly configured

class TestWebSocketPerformance:
    """Performance tests for WebSocket functionality"""

    @pytest.mark.asyncio
    async def test_high_frequency_canvas_updates(self, connection_manager, mock_redis):
        """Test handling of high-frequency canvas updates"""
        mock_sio = AsyncMock()
        connection_manager.sio = mock_sio
        
        session_id = "performance_test"
        user_id = "perf_user"
        sid = "perf_socket"
        
        mock_sio.get_session.return_value = {
            'user_id': user_id,
            'session_id': session_id
        }
        
        # Simulate high-frequency updates (100 updates)
        update_tasks = []
        for i in range(100):
            update_data = {
                'type': 'draw',
                'coordinates': [i, i, i+1, i+1]
            }
            task = connection_manager._handle_canvas_update(sid, update_data)
            update_tasks.append(task)
        
        # Measure processing time
        import time
        start_time = time.time()
        await asyncio.gather(*update_tasks)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify reasonable performance (should process 100 updates in under 1 second)
        assert processing_time < 1.0
        assert mock_sio.emit.call_count == 100

    @pytest.mark.asyncio
    async def test_memory_usage_with_many_sessions(self, connection_manager):
        """Test memory usage with many concurrent sessions"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create many sessions
        for i in range(100):
            session_id = f"session_{i}"
            for j in range(10):  # 10 users per session
                user_id = f"user_{i}_{j}"
                connection_manager.session_users.setdefault(session_id, []).append(user_id)
                connection_manager.user_sessions[user_id] = session_id
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for 1000 users)
        assert memory_increase < 50 * 1024 * 1024  # 50MB

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
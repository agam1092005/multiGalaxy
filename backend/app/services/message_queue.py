"""
Message queue service for reliable message delivery
"""
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class MessagePriority:
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class QueuedMessage:
    def __init__(
        self,
        id: str,
        queue_name: str,
        payload: Dict[str, Any],
        priority: int = MessagePriority.NORMAL,
        max_retries: int = 3,
        delay_seconds: int = 0,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.queue_name = queue_name
        self.payload = payload
        self.priority = priority
        self.max_retries = max_retries
        self.retry_count = 0
        self.delay_seconds = delay_seconds
        self.created_at = created_at or datetime.utcnow()
        self.scheduled_at = self.created_at + timedelta(seconds=delay_seconds)
        self.last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'queue_name': self.queue_name,
            'payload': self.payload,
            'priority': self.priority,
            'max_retries': self.max_retries,
            'retry_count': self.retry_count,
            'delay_seconds': self.delay_seconds,
            'created_at': self.created_at.isoformat(),
            'scheduled_at': self.scheduled_at.isoformat(),
            'last_error': self.last_error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedMessage':
        msg = cls(
            id=data['id'],
            queue_name=data['queue_name'],
            payload=data['payload'],
            priority=data['priority'],
            max_retries=data['max_retries'],
            delay_seconds=data['delay_seconds'],
            created_at=datetime.fromisoformat(data['created_at'])
        )
        msg.retry_count = data['retry_count']
        msg.scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        msg.last_error = data.get('last_error')
        return msg

class MessageQueue:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.processors: Dict[str, Callable] = {}
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.dead_letter_queue = "dlq"
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Message queue initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize message queue: {e}")
            raise

    async def enqueue(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        priority: int = MessagePriority.NORMAL,
        max_retries: int = 3,
        delay_seconds: int = 0,
        message_id: Optional[str] = None
    ) -> str:
        """Enqueue a message for processing"""
        if not self.redis_client:
            raise RuntimeError("Message queue not initialized")

        message_id = message_id or f"{queue_name}_{datetime.utcnow().timestamp()}_{id(payload)}"
        
        message = QueuedMessage(
            id=message_id,
            queue_name=queue_name,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            delay_seconds=delay_seconds
        )

        try:
            # Store message data
            await self.redis_client.hset(
                f"message:{message_id}",
                mapping=message.to_dict()
            )
            
            # Set expiration (24 hours)
            await self.redis_client.expire(f"message:{message_id}", 86400)

            # Add to appropriate queue based on delay and priority
            if delay_seconds > 0:
                # Add to delayed queue with score as scheduled timestamp
                score = message.scheduled_at.timestamp()
                await self.redis_client.zadd(f"delayed:{queue_name}", {message_id: score})
            else:
                # Add to immediate processing queue with priority as score
                await self.redis_client.zadd(f"queue:{queue_name}", {message_id: priority})

            logger.debug(f"Enqueued message {message_id} to {queue_name}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            raise

    async def dequeue(self, queue_name: str, timeout: int = 10) -> Optional[QueuedMessage]:
        """Dequeue a message for processing"""
        if not self.redis_client:
            return None

        try:
            # First, move any ready delayed messages to the main queue
            await self._process_delayed_messages(queue_name)

            # Get highest priority message
            result = await self.redis_client.bzpopmax(f"queue:{queue_name}", timeout=timeout)
            
            if not result:
                return None

            _, message_id, _ = result
            
            # Get message data
            message_data = await self.redis_client.hgetall(f"message:{message_id}")
            
            if not message_data:
                logger.warning(f"Message data not found for {message_id}")
                return None

            # Convert to QueuedMessage object
            message = QueuedMessage.from_dict(message_data)
            
            # Mark as processing
            await self.redis_client.hset(
                f"message:{message_id}",
                "processing_started_at",
                datetime.utcnow().isoformat()
            )

            return message

        except Exception as e:
            logger.error(f"Failed to dequeue message from {queue_name}: {e}")
            return None

    async def ack_message(self, message_id: str) -> bool:
        """Acknowledge successful message processing"""
        if not self.redis_client:
            return False

        try:
            # Remove message data
            await self.redis_client.delete(f"message:{message_id}")
            logger.debug(f"Acknowledged message {message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False

    async def nack_message(self, message_id: str, error: str) -> bool:
        """Negative acknowledge - retry or move to DLQ"""
        if not self.redis_client:
            return False

        try:
            # Get message data
            message_data = await self.redis_client.hgetall(f"message:{message_id}")
            
            if not message_data:
                logger.warning(f"Message data not found for {message_id}")
                return False

            message = QueuedMessage.from_dict(message_data)
            message.retry_count += 1
            message.last_error = error

            if message.retry_count >= message.max_retries:
                # Move to dead letter queue
                await self._move_to_dlq(message, error)
                logger.warning(f"Message {message_id} moved to DLQ after {message.retry_count} retries")
            else:
                # Retry with exponential backoff
                delay = min(2 ** message.retry_count, 300)  # Max 5 minutes
                message.scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
                
                # Update message data
                await self.redis_client.hset(
                    f"message:{message_id}",
                    mapping=message.to_dict()
                )
                
                # Add back to delayed queue
                score = message.scheduled_at.timestamp()
                await self.redis_client.zadd(f"delayed:{message.queue_name}", {message_id: score})
                
                logger.info(f"Message {message_id} scheduled for retry in {delay} seconds")

            return True

        except Exception as e:
            logger.error(f"Failed to nack message {message_id}: {e}")
            return False

    async def register_processor(self, queue_name: str, processor: Callable[[Dict[str, Any]], bool]):
        """Register a message processor for a queue"""
        self.processors[queue_name] = processor
        logger.info(f"Registered processor for queue: {queue_name}")

    async def start_workers(self, num_workers: int = 3):
        """Start worker processes"""
        if self.is_running:
            logger.warning("Workers already running")
            return

        self.is_running = True
        
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        logger.info(f"Started {num_workers} message queue workers")

    async def stop_workers(self):
        """Stop all worker processes"""
        self.is_running = False
        
        for task in self.worker_tasks:
            task.cancel()
        
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.worker_tasks.clear()
        logger.info("Stopped all message queue workers")

    async def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get queue statistics"""
        if not self.redis_client:
            return {}

        try:
            immediate_count = await self.redis_client.zcard(f"queue:{queue_name}")
            delayed_count = await self.redis_client.zcard(f"delayed:{queue_name}")
            dlq_count = await self.redis_client.zcard(f"dlq:{queue_name}")

            return {
                'immediate': immediate_count,
                'delayed': delayed_count,
                'dead_letter': dlq_count,
                'total': immediate_count + delayed_count
            }

        except Exception as e:
            logger.error(f"Failed to get queue stats for {queue_name}: {e}")
            return {}

    async def _worker(self, worker_id: str):
        """Worker process for handling messages"""
        logger.info(f"Worker {worker_id} started")
        
        while self.is_running:
            try:
                # Process messages from all registered queues
                for queue_name in self.processors.keys():
                    message = await self.dequeue(queue_name, timeout=1)
                    
                    if message:
                        await self._process_message(message, worker_id)

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} stopped")

    async def _process_message(self, message: QueuedMessage, worker_id: str):
        """Process a single message"""
        processor = self.processors.get(message.queue_name)
        
        if not processor:
            logger.error(f"No processor registered for queue: {message.queue_name}")
            await self.nack_message(message.id, "No processor registered")
            return

        try:
            logger.debug(f"Worker {worker_id} processing message {message.id}")
            
            # Process the message
            success = await processor(message.payload)
            
            if success:
                await self.ack_message(message.id)
                logger.debug(f"Message {message.id} processed successfully")
            else:
                await self.nack_message(message.id, "Processor returned False")

        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            logger.error(f"Error processing message {message.id}: {error_msg}")
            await self.nack_message(message.id, error_msg)

    async def _process_delayed_messages(self, queue_name: str):
        """Move ready delayed messages to the main queue"""
        if not self.redis_client:
            return

        try:
            now = datetime.utcnow().timestamp()
            
            # Get messages that are ready to be processed
            ready_messages = await self.redis_client.zrangebyscore(
                f"delayed:{queue_name}",
                0,
                now,
                withscores=True
            )

            for message_id, _ in ready_messages:
                # Get message data to determine priority
                message_data = await self.redis_client.hgetall(f"message:{message_id}")
                
                if message_data:
                    priority = int(message_data.get('priority', MessagePriority.NORMAL))
                    
                    # Move to main queue
                    await self.redis_client.zadd(f"queue:{queue_name}", {message_id: priority})
                    
                    # Remove from delayed queue
                    await self.redis_client.zrem(f"delayed:{queue_name}", message_id)

        except Exception as e:
            logger.error(f"Error processing delayed messages for {queue_name}: {e}")

    async def _move_to_dlq(self, message: QueuedMessage, error: str):
        """Move message to dead letter queue"""
        if not self.redis_client:
            return

        try:
            # Add error information
            dlq_data = message.to_dict()
            dlq_data['moved_to_dlq_at'] = datetime.utcnow().isoformat()
            dlq_data['final_error'] = error

            # Store in DLQ
            await self.redis_client.hset(f"dlq_message:{message.id}", mapping=dlq_data)
            await self.redis_client.zadd(f"dlq:{message.queue_name}", {message.id: datetime.utcnow().timestamp()})
            
            # Remove original message
            await self.redis_client.delete(f"message:{message.id}")

        except Exception as e:
            logger.error(f"Failed to move message {message.id} to DLQ: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_workers()
        
        if self.redis_client:
            await self.redis_client.close()

# Global message queue instance
message_queue = MessageQueue()
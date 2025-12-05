"""
RabbitMQ connection and publisher for ingestion service.

Events are published to a queue for the analytics_service to process.
"""

import json
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import aio_pika
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractChannel, AbstractConnection

from app.config import settings


# =============================================================================
# GLOBAL CONNECTION
# =============================================================================
# We maintain a single connection that's reused across requests.

_connection: Optional[AbstractConnection] = None
_channel: Optional[AbstractChannel] = None


async def connect() -> None:
    """
    Establish connection to RabbitMQ.
    
    Called at application startup.
    """
    global _connection, _channel
    
    print(f"📡 Connecting to RabbitMQ at {settings.rabbitmq_url}...")
    
    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()
    
    # Declare the queue (creates it if it doesn't exist)
    await _channel.declare_queue(
        settings.events_queue,
        durable=True,  # Queue survives broker restart
    )
    
    print(f"✅ Connected to RabbitMQ, queue '{settings.events_queue}' ready")


async def disconnect() -> None:
    """
    Close RabbitMQ connection.
    
    Called at application shutdown.
    """
    global _connection, _channel
    
    if _channel:
        await _channel.close()
        _channel = None
    
    if _connection:
        await _connection.close()
        _connection = None
    
    print("👋 Disconnected from RabbitMQ")


async def publish_event(event_data: Dict[str, Any]) -> None:
    """
    Publish an event to the queue for analytics processing.
    
    Args:
        event_data: Dictionary containing event information
                   (id, project_id, source, event_type, severity, etc.)
    """
    if _channel is None:
        raise RuntimeError("RabbitMQ not connected")
    
    # Serialize to JSON
    message_body = json.dumps(event_data, default=str).encode()
    
    # Create message with persistence
    message = Message(
        body=message_body,
        delivery_mode=DeliveryMode.PERSISTENT,  # Survives broker restart
        content_type="application/json",
    )
    
    # Publish to the default exchange with queue name as routing key
    await _channel.default_exchange.publish(
        message,
        routing_key=settings.events_queue,
    )


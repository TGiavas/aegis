"""
RabbitMQ consumer for analytics service.

Consumes events from the queue and processes them through alert rules.
"""

import asyncio
import json
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import select

from app.config import settings
from app.db import Alert, AsyncSessionLocal
from app.rules import evaluate_event


async def process_message(message: AbstractIncomingMessage) -> None:
    """
    Process a single event message.

    1. Parse the event JSON
    2. Evaluate alert rules (loaded from database)
    3. Create alerts if triggered (avoiding duplicates)
    4. Acknowledge the message
    """
    async with message.process():
        try:
            # Parse event data
            event = json.loads(message.body.decode())
            project_id = event.get("project_id")

            print(
                f"📥 Processing event: {event.get('event_type')} from {event.get('source')}"
            )

            # Use a single DB session for both rule evaluation and alert creation
            async with AsyncSessionLocal() as db:
                # Evaluate rules (now fetched from database)
                triggers = await evaluate_event(db, event)

                for trigger in triggers:
                    # Check for existing open alert (avoid duplicates)
                    existing = await check_existing_alert(
                        db, project_id, trigger.rule_name
                    )

                    if existing:
                        print(f"⏭️  Alert already exists: {trigger.rule_name}")
                        continue

                    # Create new alert
                    alert = Alert(
                        project_id=project_id,
                        rule_name=trigger.rule_name,
                        level=trigger.level,
                        message=trigger.message,
                    )
                    db.add(alert)
                    await db.commit()

                    print(
                        f"🚨 Alert created: [{trigger.level}] {trigger.rule_name}"
                    )

        except Exception as e:
            print(f"❌ Error processing message: {e}")
            # Message will be requeued if not acknowledged


async def check_existing_alert(
    db,
    project_id: int,
    rule_name: str,
) -> Optional[Alert]:
    """
    Check if there's an existing unresolved alert for this rule.

    This prevents duplicate alerts for the same condition.
    """
    query = select(Alert).where(
        Alert.project_id == project_id,
        Alert.rule_name == rule_name,
        Alert.resolved_at.is_(None),  # Only open alerts
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def start_consumer() -> None:
    """
    Start consuming events from RabbitMQ.

    This runs as a background task and processes events indefinitely.
    """
    print(f"📡 Connecting to RabbitMQ at {settings.rabbitmq_url}...")

    # Connect with retry
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()

    # Set prefetch to process one message at a time
    await channel.set_qos(prefetch_count=1)

    # Declare queue (must match ingestion_service)
    queue = await channel.declare_queue(
        settings.events_queue,
        durable=True,
    )

    print(f"✅ Connected! Consuming from queue '{settings.events_queue}'...")

    # Start consuming
    await queue.consume(process_message)

    # Keep running
    try:
        await asyncio.Future()  # Run forever
    finally:
        await connection.close()

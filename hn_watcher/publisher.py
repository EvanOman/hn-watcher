import io
import json
from contextlib import contextmanager
from typing import Generator, Optional

import avro.io
import avro.schema
import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exchange_type import ExchangeType

from hn_watcher.models import Comment


class PikaPublisher:
    """Implementation of MessagePublisher using Pika and Avro."""

    # Avro schema for HackerNews comments
    COMMENT_SCHEMA = {
        "namespace": "hn_watcher.comment",
        "type": "record",
        "name": "Comment",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "parent_id", "type": ["int", "null"]},
            {"name": "by", "type": ["string", "null"]},
            {"name": "time", "type": ["int", "null"]},
            {"name": "text", "type": ["string", "null"]},
            {"name": "deleted", "type": ["boolean", "null"], "default": False},
            {"name": "dead", "type": ["boolean", "null"], "default": False},
        ],
    }

    def __init__(
        self,
        host: str = "localhost",
        exchange: str = "hackernews",
        exchange_type: ExchangeType = ExchangeType.topic,
        durable: bool = True,
        username: str = "guest",
        password: str = "guest",
    ):
        """
        Initialize the Pika publisher.

        Args:
            host: RabbitMQ host
            exchange: Exchange name
            exchange_type: Exchange type (topic, direct, fanout, etc.)
            durable: Whether the exchange should be durable
            username: RabbitMQ username
            password: RabbitMQ password
        """
        self.host = host
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.durable = durable
        self.username = username
        self.password = password
        self._connection: Optional[BlockingConnection] = None
        self._channel: Optional[BlockingChannel] = None
        self.avro_schema = avro.schema.parse(json.dumps(self.COMMENT_SCHEMA))

    @property
    def is_connected(self) -> bool:
        """Check if there is an active connection."""
        return (
            self._connection is not None
            and not self._connection.is_closed
            and self._channel is not None
            and not self._channel.is_closed
        )

    @property
    def channel(self) -> BlockingChannel:
        """Get the active channel."""
        if not self.is_connected:
            raise RuntimeError("Not connected to RabbitMQ")
        if self._channel is None:
            raise RuntimeError("Channel is not open")
        return self._channel

    @contextmanager
    def connection(self) -> Generator[BlockingChannel, None, None]:
        """
        Context manager for handling RabbitMQ connections.

        Yields:
            An active channel for publishing messages.

        Example:
            ```python
            with publisher.connection() as channel:
                channel.basic_publish(...)
            ```
        """
        try:
            if not self.is_connected:
                credentials = pika.PlainCredentials(self.username, self.password)
                self._connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=self.host, credentials=credentials)
                )
                self._channel = self._connection.channel()
                self._channel.exchange_declare(
                    exchange=self.exchange,
                    exchange_type=self.exchange_type,
                    durable=self.durable,
                )
            yield self.channel
        except Exception as e:
            self.close()  # Ensure cleanup on error
            raise e

    def publish_comment(
        self, comment: Comment, routing_key: str = "comment.new"
    ) -> None:
        """
        Publish a comment to the RabbitMQ exchange using Avro encoding.

        Args:
            comment: HackerNews comment to publish
            routing_key: Routing key for the message
        """
        # Prepare the record for Avro serialization
        record = {
            "id": comment.id,
            "parent_id": comment.parent_id,
            "by": comment.by,
            "time": comment.time,
            "text": comment.text,
            "deleted": comment.deleted,
            "dead": comment.dead,
        }

        # Serialize the record using Avro
        buf = io.BytesIO()
        encoder = avro.io.BinaryEncoder(buf)
        writer = avro.io.DatumWriter(self.avro_schema)
        writer.write(record, encoder)
        avro_bytes = buf.getvalue()

        # Publish the message using the context manager
        with self.connection() as channel:
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=avro_bytes,
                properties=pika.BasicProperties(
                    content_type="avro/binary",
                    delivery_mode=2,  # Persistent
                ),
            )

    def close(self) -> None:
        """Close the connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            self._connection.close()
        self._connection = None
        self._channel = None

    def __enter__(self) -> "PikaPublisher":
        """Support using the publisher as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure connection is closed when exiting context."""
        self.close()

"""
Tests for the publisher module.
"""

import io
from unittest.mock import MagicMock, patch

import avro.io
import avro.schema
import pika
import pytest
from pika.exchange_type import ExchangeType

from hn_watcher.models import Comment
from hn_watcher.publisher import PikaPublisher


class TestPikaPublisher:
    """Tests for the PikaPublisher class."""
    
    def test_init(self):
        """Test initializing the publisher."""
        publisher = PikaPublisher()
        assert publisher.host == "localhost"
        assert publisher.exchange == "hackernews"
        assert publisher.exchange_type == ExchangeType.topic
        assert publisher.durable is True
        assert publisher._connection is None
        assert publisher._channel is None
        assert publisher.avro_schema is not None
        
    def test_is_connected_property(self):
        """Test the is_connected property."""
        publisher = PikaPublisher()
        assert not publisher.is_connected
        
        # Mock a connection
        publisher._connection = MagicMock()
        publisher._connection.is_closed = False
        publisher._channel = MagicMock()
        publisher._channel.is_closed = False
        assert publisher.is_connected
        
        # Test with closed connection
        publisher._connection.is_closed = True
        assert not publisher.is_connected
        
        # Test with closed channel
        publisher._connection.is_closed = False
        publisher._channel.is_closed = True
        assert not publisher.is_connected
    
    def test_channel_property(self):
        """Test the channel property."""
        publisher = PikaPublisher()
        
        # Should raise when not connected
        with pytest.raises(RuntimeError, match="Not connected to RabbitMQ"):
            _ = publisher.channel
        
        # Should raise when channel is None
        publisher._connection = MagicMock()
        publisher._connection.is_closed = False
        publisher._channel = None
        with pytest.raises(RuntimeError, match="Not connected to RabbitMQ"):
            _ = publisher.channel
        
        # Should return channel when properly connected
        publisher._channel = MagicMock()
        publisher._channel.is_closed = False
        assert publisher.channel == publisher._channel
    
    def test_connection_context_manager(self):
        """Test the connection context manager."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_connection.channel.return_value = mock_channel
            mock_connection.is_closed = False
            mock_channel.is_closed = False
            mock_connection_class.return_value = mock_connection
            
            publisher = PikaPublisher()
            
            # Test normal usage
            with publisher.connection() as channel:
                assert channel == mock_channel
                mock_connection_class.assert_called_once()
                channel.exchange_declare.assert_called_once_with(
                    exchange=publisher.exchange,
                    exchange_type=publisher.exchange_type,
                    durable=publisher.durable,
                )
            
            # Test reuse of existing connection
            mock_connection_class.reset_mock()
            publisher._connection = mock_connection
            publisher._connection.is_closed = False
            publisher._channel = mock_channel
            publisher._channel.is_closed = False
            
            with publisher.connection() as channel:
                assert channel == mock_channel
                mock_connection_class.assert_not_called()  # Should reuse existing connection
            
            # Test cleanup on error
            mock_connection_class.reset_mock()
            mock_channel.basic_publish.side_effect = Exception("Test error")
            
            with pytest.raises(Exception, match="Test error"):
                with publisher.connection() as channel:
                    channel.basic_publish()
            
            assert publisher._connection is None
            assert publisher._channel is None
    
    def test_publish_comment(self):
        """Test publishing a comment."""
        # Create a sample comment using the Pydantic model
        comment = Comment(
            id=1001,
            parent_id=12345,
            by="testuser",
            time=1617235300,
            text="Test comment",
        )
        
        with patch("pika.BlockingConnection") as mock_connection_class:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_connection.channel.return_value = mock_channel
            mock_connection.is_closed = False
            mock_channel.is_closed = False
            mock_connection_class.return_value = mock_connection
            
            publisher = PikaPublisher()
            
            # Use real Avro serialization to test the encoding
            publisher.publish_comment(comment)
            
            # Verify basic_publish was called
            mock_channel.basic_publish.assert_called_once()
            
            # Get the call arguments
            call_args = mock_channel.basic_publish.call_args[1]
            assert call_args["exchange"] == publisher.exchange
            assert call_args["routing_key"] == "comment.new"
            
            # Verify properties
            properties = call_args["properties"]
            assert properties.content_type == "avro/binary"
            assert properties.delivery_mode == 2  # Persistent
            
            # Verify the Avro serialization
            body = call_args["body"]
            buf = io.BytesIO(body)
            decoder = avro.io.BinaryDecoder(buf)
            reader = avro.io.DatumReader(publisher.avro_schema)
            result = reader.read(decoder)
            
            assert result["id"] == comment.id
            assert result["parent_id"] == comment.parent_id
            assert result["by"] == comment.by
            assert result["time"] == comment.time
            assert result["text"] == comment.text
            assert result["deleted"] is False
            assert result["dead"] is False
    
    def test_close(self):
        """Test closing the connection."""
        publisher = PikaPublisher()
        
        # Test with no connection
        publisher.close()
        assert publisher._connection is None
        assert publisher._channel is None
        
        # Test with open connection
        mock_connection = MagicMock()
        mock_connection.is_closed = False
        publisher._connection = mock_connection
        publisher._channel = MagicMock()
        
        publisher.close()
        
        mock_connection.close.assert_called_once()
        assert publisher._connection is None
        assert publisher._channel is None
    
    def test_context_manager(self):
        """Test using the publisher as a context manager."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_connection.channel.return_value = mock_channel
            mock_connection.is_closed = False
            mock_channel.is_closed = False
            mock_connection_class.return_value = mock_connection
            
            # Test normal usage
            with PikaPublisher() as publisher:
                # Connect to RabbitMQ
                with publisher.connection():
                    assert isinstance(publisher, PikaPublisher)
                    assert publisher._connection == mock_connection
                    assert publisher._channel == mock_channel
            
            # Test cleanup on error
            mock_channel.basic_publish.side_effect = Exception("Test error")
            
            with pytest.raises(Exception, match="Test error"):
                with PikaPublisher() as publisher:
                    publisher.publish_comment(Comment(id=1001))
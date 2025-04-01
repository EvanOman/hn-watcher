"""
Pytest configuration and fixtures for HN Watcher tests.
"""

import os
import tempfile
from typing import Any, Dict, List, Optional

import pytest
from pika.exchange_type import ExchangeType

from hn_watcher.db import CommentDatabase
from hn_watcher.hn import HNContext
from hn_watcher.models import Comment


class MockApiClient:
    """Mock API client for testing."""
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        """Initialize with predefined responses."""
        self.responses = responses or {}
        self.get_calls: List[str] = []
    
    def get(self, url: str) -> Any:
        """Return a predefined response for the URL or a default empty dict."""
        self.get_calls.append(url)
        return self.responses.get(url, {})
    
    def get_top_level_comments(self, item_id: int) -> List[Dict[str, Any]]:
        """Mock getting top-level comments for an item."""
        return []
    
    def get_comments(self, item_id: int, max_depth: Optional[int] = None) -> List[Dict[str, Any]]:
        """Mock getting all comments for an item."""
        return []


class MockPublisher:
    """Mock message publisher for testing."""
    
    def __init__(self):
        """Initialize the mock publisher."""
        self.published_comments: List[Comment] = []
        self.routing_keys: List[str] = []
        self.host = "localhost"
        self.exchange = "hackernews"
        self.exchange_type = ExchangeType.topic
        self.durable = True
    
    def publish_comment(self, comment: Comment, routing_key: str) -> None:
        """Record the published comment."""
        self.published_comments.append(comment)
        self.routing_keys.append(routing_key)
    
    def connect(self) -> None:
        """Mock connection establishment."""
        pass
    
    def close(self) -> None:
        """Mock connection closing."""
        pass


@pytest.fixture
def temp_db_path() -> str:
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def mock_api_client() -> MockApiClient:
    """Return a mock API client."""
    return MockApiClient()


@pytest.fixture
def mock_publisher() -> MockPublisher:
    """Return a mock message publisher."""
    return MockPublisher()


@pytest.fixture
def mock_context(mock_api_client: MockApiClient, mock_publisher: MockPublisher, temp_db_path: str) -> HNContext:
    """Return a mock HN context."""
    return HNContext(
        api_client=mock_api_client,
        db=CommentDatabase(temp_db_path),
        publisher=mock_publisher,
    )


@pytest.fixture
def sample_item() -> Dict[str, Any]:
    """Return a sample HN item (story)."""
    return {
        "id": 12345,
        "title": "Test Story",
        "by": "testuser",
        "time": 1617235200,
        "text": "Test story text",
        "kids": [1001, 1002, 1003],
    }


@pytest.fixture
def sample_comments() -> List[Dict[str, Any]]:
    """Return a list of sample comments."""
    return [
        {
            "id": 1001,
            "parent": 12345,
            "by": "user1",
            "time": 1617235300,
            "text": "Comment 1",
        },
        {
            "id": 1002,
            "parent": 12345,
            "by": "user2",
            "time": 1617235400,
            "text": "Comment 2",
        },
        {
            "id": 1003,
            "parent": 12345,
            "by": "user3",
            "time": 1617235500,
            "text": "Comment 3",
        },
    ]
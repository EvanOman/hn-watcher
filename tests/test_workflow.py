"""
Tests for the workflow module.
"""

from unittest.mock import patch

import pytest

from hn_watcher.models import Comment
from hn_watcher.workflow import NewCommentPublisher


class TestNewCommentPublisher:
    """Tests for the NewCommentPublisher class."""
    
    def test_init(self, mock_context):
        """Test initializing the publisher."""
        publisher = NewCommentPublisher(mock_context)
        assert publisher.context == mock_context
        assert publisher.hn_api is not None
        
    def test_publish_new_comments_no_comments(self, mock_context, mock_api_client):
        """Test getting new comments when there are none."""
        # Set up mock responses
        mock_api_client.responses = {
            "https://hacker-news.firebaseio.com/v0/item/12345.json": {
                "id": 12345,
                "title": "Test Story",
                "kids": [],  # No comments
            }
        }
        
        publisher = NewCommentPublisher(mock_context)
        result = publisher.publish_new_comments(12345)
        
        assert result == []
        assert len(mock_api_client.get_calls) == 1
        
    def test_publish_new_comments_with_comments(
        self, mock_context, mock_api_client, sample_item, sample_comments
    ):
        """Test getting new comments when there are some."""
        # Set up mock responses
        base_url = "https://hacker-news.firebaseio.com/v0"
        mock_api_client.responses = {
            f"{base_url}/item/{sample_item['id']}.json": sample_item,
            f"{base_url}/item/{sample_comments[0]['id']}.json": sample_comments[0],
            f"{base_url}/item/{sample_comments[1]['id']}.json": sample_comments[1],
            f"{base_url}/item/{sample_comments[2]['id']}.json": sample_comments[2],
        }
        
        publisher = NewCommentPublisher(mock_context)
        result = publisher.publish_new_comments(sample_item["id"])
        
        assert len(result) == 3
        assert all(isinstance(comment, Comment) for comment in result)
        assert [comment.id for comment in result] == [1001, 1002, 1003]
        
        # Verify API calls
        assert len(mock_api_client.get_calls) == 4  # item + 3 comments
        
        # Verify comments were published
        mock_publisher = mock_context.publisher
        assert len(mock_publisher.published_comments) == 3
        assert all(isinstance(comment, Comment) for comment in mock_publisher.published_comments)
        assert all(key == f"comment.item.{sample_item['id']}" for key in mock_publisher.routing_keys)
        
    def test_publish_new_comments_skip_existing(
        self, mock_context, mock_api_client, temp_db_path, sample_item, sample_comments
    ):
        """Test that existing comments are skipped."""
        # Set up mock responses
        base_url = "https://hacker-news.firebaseio.com/v0"
        mock_api_client.responses = {
            f"{base_url}/item/{sample_item['id']}.json": sample_item,
            f"{base_url}/item/{sample_comments[0]['id']}.json": sample_comments[0],
            f"{base_url}/item/{sample_comments[1]['id']}.json": sample_comments[1],
            f"{base_url}/item/{sample_comments[2]['id']}.json": sample_comments[2],
        }
        
        # Add one comment to the database so it will be skipped
        mock_context.db.add_comment(sample_comments[0])
        
        publisher = NewCommentPublisher(mock_context)
        result = publisher.publish_new_comments(sample_item["id"])
        
        assert len(result) == 2
        assert all(isinstance(comment, Comment) for comment in result)
        assert [comment.id for comment in result] == [1002, 1003]
        
        # Verify API calls (should still call for all 3 comment ids to check existence)
        assert len(mock_api_client.get_calls) == 3  # item + 2 comments (skips existing)
        
        # Verify only 2 comments were published
        mock_publisher = mock_context.publisher
        assert len(mock_publisher.published_comments) == 2
        assert all(isinstance(comment, Comment) for comment in mock_publisher.published_comments)
        
    def test_publish_new_comments_skip_deleted(
        self, mock_context, mock_api_client, sample_item, sample_comments
    ):
        """Test that deleted comments are skipped."""
        # Mark one comment as deleted
        sample_comments[1]["deleted"] = True
        
        # Set up mock responses
        base_url = "https://hacker-news.firebaseio.com/v0"
        mock_api_client.responses = {
            f"{base_url}/item/{sample_item['id']}.json": sample_item,
            f"{base_url}/item/{sample_comments[0]['id']}.json": sample_comments[0],
            f"{base_url}/item/{sample_comments[1]['id']}.json": sample_comments[1],  # Deleted
            f"{base_url}/item/{sample_comments[2]['id']}.json": sample_comments[2],
        }
        
        publisher = NewCommentPublisher(mock_context)
        result = publisher.publish_new_comments(sample_item["id"])
        
        assert len(result) == 2
        assert all(isinstance(comment, Comment) for comment in result)
        assert [comment.id for comment in result] == [1001, 1003]
        
        # Verify API calls
        assert len(mock_api_client.get_calls) == 4  # item + 3 comments
        
        # Verify only 2 comments were published
        mock_publisher = mock_context.publisher
        assert len(mock_publisher.published_comments) == 2
        assert all(isinstance(comment, Comment) for comment in mock_publisher.published_comments) 
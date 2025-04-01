"""
Tests for the database module.
"""

import json
import os
import sqlite3

import pytest

from hn_watcher.db import CommentDatabase
from hn_watcher.models import Comment


class TestCommentDatabase:
    """Tests for the CommentDatabase class."""
    
    def test_init(self, temp_db_path):
        """Test initializing the database."""
        db = CommentDatabase(temp_db_path)
        
        # Verify the database connection was created
        assert db.db_path == temp_db_path
        assert db.conn is not None
        
        # Verify the database file exists
        assert os.path.exists(temp_db_path)
        
        # Verify the table was created
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'")
        assert cursor.fetchone() is not None
        
        # Clean up
        db.close()
    
    def test_comment_exists(self, temp_db_path):
        """Test checking if a comment exists."""
        db = CommentDatabase(temp_db_path)
        
        # Initially, no comments should exist
        assert db.comment_exists(1001) is False
        
        # Add a comment
        comment = Comment(
            id=1001,
            parent_id=12345,
            by="testuser",
            time=1617235300,
            text="Test comment",
        )
        db.add_comment(comment.model_dump())
        
        # Now it should exist
        assert db.comment_exists(1001) is True
        
        # Another comment still shouldn't exist
        assert db.comment_exists(1002) is False
        
        # Clean up
        db.close()
    
    def test_add_comment(self, temp_db_path):
        """Test adding a comment to the database."""
        db = CommentDatabase(temp_db_path)
        
        comment = Comment(
            id=1001,
            parent_id=12345,
            by="testuser",
            time=1617235300,
            text="Test comment",
        )
        
        # Add the comment
        db.add_comment(comment.model_dump())
        
        # Verify it was added
        cursor = db.conn.cursor()
        cursor.execute("SELECT id, parent_id, by, time, text, raw_data FROM comments WHERE id = ?", (1001,))
        result = cursor.fetchone()
        
        assert result is not None
        assert result["id"] == 1001
        assert result["parent_id"] == 12345
        assert result["by"] == "testuser"
        assert result["time"] == 1617235300
        assert result["text"] == "Test comment"
        assert json.loads(result["raw_data"]) == comment.model_dump()
        
        # Adding it again should not cause an error
        db.add_comment(comment.model_dump())
        
        # Check if there's still only one record
        cursor.execute("SELECT COUNT(*) as count FROM comments WHERE id = ?", (1001,))
        assert cursor.fetchone()["count"] == 1
        
        # Clean up
        db.close()
    
    def test_get_comment(self, temp_db_path):
        """Test retrieving a comment from the database."""
        db = CommentDatabase(temp_db_path)
        
        # Initially, getting a non-existent comment should return None
        assert db.get_comment(1001) is None
        
        # Add a comment
        comment = Comment(
            id=1001,
            parent_id=12345,
            by="testuser",
            time=1617235300,
            text="Test comment",
        )
        db.add_comment(comment.model_dump())
        
        # Now retrieving it should work
        result = db.get_comment(1001)
        assert result == comment.model_dump()
        
        # Clean up
        db.close()
    
    def test_get_all_comments(self, temp_db_path):
        """Test retrieving all comments from the database."""
        db = CommentDatabase(temp_db_path)
        
        # Initially, there should be no comments
        assert db.get_all_comments() == []
        
        # Add some comments
        comments = [
            Comment(
                id=1001,
                parent_id=12345,
                by="user1",
                time=1617235300,
                text="Comment 1",
            ),
            Comment(
                id=1002,
                parent_id=12345,
                by="user2",
                time=1617235400,
                text="Comment 2",
            ),
        ]
        
        for comment in comments:
            db.add_comment(comment.model_dump())
        
        # Now retrieving all should return both
        result = db.get_all_comments()
        assert len(result) == 2
        
        # The result should contain both comments
        ids = [comment["id"] for comment in result]
        assert 1001 in ids
        assert 1002 in ids
        
        # Clean up
        db.close()
    
    def test_close(self, temp_db_path):
        """Test closing the database connection."""
        db = CommentDatabase(temp_db_path)
        
        # Close the connection
        db.close()
        
        # Attempting operations should fail now
        with pytest.raises(sqlite3.ProgrammingError):
            db.comment_exists(1001)
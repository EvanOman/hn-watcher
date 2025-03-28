import json
import sqlite3
from typing import Any, Dict, List, Optional


class CommentDatabase:
    """
    Handles storage and retrieval of HackerNews comments in a SQLite database.
    """
    
    def __init__(self, db_path: str = "hn_comments.db"):
        """
        Initialize the database connection and create table if it doesn't exist.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create the necessary tables if they don't already exist."""
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,
            by TEXT,
            time INTEGER,
            text TEXT,
            raw_data TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.conn.commit()
    
    def comment_exists(self, comment_id: int) -> bool:
        """
        Check if a comment exists in the database.
        
        Args:
            comment_id: The ID of the comment to check
            
        Returns:
            True if the comment exists, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM comments WHERE id = ?", (comment_id,))
        return cursor.fetchone() is not None
    
    def add_comment(self, comment: Dict[str, Any]) -> None:
        """
        Add a comment to the database.
        
        Args:
            comment: The comment data from HackerNews API
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO comments (id, parent_id, by, time, text, raw_data) VALUES (?, ?, ?, ?, ?, ?)",
            (
                comment.get('id'),
                comment.get('parent'),
                comment.get('by'),
                comment.get('time'),
                comment.get('text', ''),
                json.dumps(comment)
            )
        )
        self.conn.commit()
    
    def get_comment(self, comment_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a comment from the database.
        
        Args:
            comment_id: The ID of the comment to retrieve
            
        Returns:
            The comment data as a dictionary, or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT raw_data FROM comments WHERE id = ?", (comment_id,))
        result = cursor.fetchone()
        
        if result:
            return json.loads(result['raw_data'])
        return None
    
    def get_all_comments(self) -> List[Dict[str, Any]]:
        """
        Retrieve all comments from the database.
        
        Returns:
            A list of all comments as dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT raw_data FROM comments")
        return [json.loads(row['raw_data']) for row in cursor.fetchall()]
    
    def close(self):
        """Close the database connection."""
        self.conn.close() 
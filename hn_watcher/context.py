from hn_watcher.db import CommentDatabase
from hn_watcher.hn import HNContext, RequestsClient


class HNContextProvider:
    """
    Service locator/provider for Hacker News contexts.
    Follows the patterns in "Architecture Patterns with Python".
    """
    
    @staticmethod
    def get_default_context(db_path: str = "hn_comments.db") -> HNContext:
        """
        Factory method to create a default context with standard configuration.
        
        Args:
            db_path: Path to the SQLite database file
            
        Returns:
            A configured HNContext
        """
        db = CommentDatabase(db_path)
        api_client = RequestsClient()
        
        return HNContext(
            api_client=api_client,
            db=db,
            request_delay=0.1,  # Default delay
            base_url="https://hacker-news.firebaseio.com/v0"
        )
    
    @staticmethod
    def get_testing_context() -> HNContext:
        """
        Factory method to create a context suitable for testing.
        
        Returns:
            A HNContext configured for testing
        """
        # In a real implementation, you might want to use an in-memory DB
        # and a mock API client
        db = CommentDatabase(":memory:")
        
        return HNContext(
            db=db,
            request_delay=0.0  # No delay for testing
        ) 
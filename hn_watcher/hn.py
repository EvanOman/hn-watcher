import sys
import time
from typing import Any, Optional, Protocol

import requests

from hn_watcher.db import CommentDatabase
from hn_watcher.models import Comment
from hn_watcher.publisher import PikaPublisher


class ApiClient(Protocol):
    """Protocol defining the interface for an API client."""

    def get(self, url: str) -> Any:
        """Make a GET request to the specified URL."""
        ...


class RequestsClient:
    """Implementation of ApiClient using the requests library."""

    def get(self, url: str) -> Any:
        """Make a GET request to the specified URL."""
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


class HNContext:
    """
    Context object for Hacker News API operations.
    Contains all dependencies needed by the API client.
    """

    def __init__(
        self,
        api_client: ApiClient,
        db: CommentDatabase,
        publisher: PikaPublisher,
        request_delay: float = 0.1,
        base_url: str = "https://hacker-news.firebaseio.com/v0",
    ):
        """
        Initialize the Hacker News context.

        Args:
            api_client: Client for making HTTP requests
            db: Database for storing comments
            publisher: Message publisher for sending comments to a message broker
            request_delay: Time to wait between API requests in seconds
            base_url: Base URL for the Hacker News API
        """
        self.api_client = api_client or RequestsClient()
        self.db = db
        self.publisher = publisher
        self.request_delay = request_delay
        self.base_url = base_url

    def close(self):
        """Close all connections."""
        if self.db:
            self.db.close()

        if self.publisher:
            self.publisher.close()


class HackerNewsAPI:
    """
    A client for the Hacker News API that can retrieve comments from a specific item.
    """

    def __init__(self, context: HNContext) -> None:
        """
        Initialize the HackerNews API client.

        Args:
            context: Context object containing dependencies
        """
        self.context = context

    def get_item(self, item_id: int) -> Optional[dict[str, Any]]:
        """
        Retrieve an item (story, comment, etc.) from the HackerNews API.

        Args:
            item_id: The ID of the item to retrieve

        Returns:
            The item data as a dictionary, or None if the item doesn't exist
        """
        url = f"{self.context.base_url}/item/{item_id}.json"
        result = self.context.api_client.get(url)
        time.sleep(self.context.request_delay)  # Be nice to the API

        return result

    def get_comments(self, item_id: int, max_depth: int = sys.maxsize) -> list[Comment]:
        """
        Retrieve comments for a given Hacker News item with optional depth limit.

        Args:
            item_id: The ID of the HN item (story, poll, etc.)
            max_depth: Maximum depth of comments to retrieve (default: unlimited)

        Returns:
            A list of comments in the thread up to the specified depth
        """
        item = self.get_item(item_id)
        if not item:
            return []

        return self._get_all_comments(item, max_depth)

    def _get_all_comments(
        self,
        item: dict[str, Any],
        max_depth: int = sys.maxsize,
        current_depth: int = 0,
    ) -> list[Comment]:
        """
        Recursively collect comments from an item up to a specified depth.

        Args:
            item: The parent item or comment
            max_depth: Maximum depth of comments to retrieve
            current_depth: Current depth in the comment tree

        Returns:
            A list of comments in the thread up to the specified depth
        """
        # If we've reached the maximum depth or the item has no kids, return empty list
        if current_depth >= max_depth or "kids" not in item or not item["kids"]:
            return []

        comments = []

        # Retrieve each comment by its ID
        for kid_id in item["kids"]:
            comment_dict = self.get_item(kid_id)
            if not comment_dict:
                continue

            # Skip deleted or dead comments
            if comment_dict.get("deleted") or comment_dict.get("dead"):
                continue

            # Convert to Comment model and add to our list
            comment = Comment(**comment_dict)
            comments.append(comment)

            # Recursively get child comments and extend the list
            child_comments = self._get_all_comments(
                comment_dict, max_depth, current_depth + 1
            )
            comments.extend(child_comments)

        return comments

    def get_top_level_comments(self, item_id: int) -> list[Comment]:
        """
        Retrieve only top-level comments for a given Hacker News item.

        Args:
            item_id: The ID of the HN item (story, poll, etc.)

        Returns:
            A list of only top-level comments in the thread
        """
        item = self.get_item(item_id)
        if not item or "kids" not in item or not item["kids"]:
            return []

        comments = []

        # Retrieve only top-level comments by their ID
        for kid_id in item["kids"]:
            comment_dict = self.get_item(kid_id)
            if not comment_dict:
                continue

            # Skip deleted or dead comments
            if comment_dict.get("deleted") or comment_dict.get("dead"):
                continue

            # Convert to Comment model and add to our list
            comment = Comment(**comment_dict)
            comments.append(comment)

        return comments

    def get_new_top_level_comments(self, item_id: int) -> list[Comment]:
        """
        Retrieve only new top-level comments for a given Hacker News item.
        Checks the database to avoid fetching comments we've already seen.

        Args:
            item_id: The ID of the HN item (story, poll, etc.)

        Returns:
            A list of only new top-level comments in the thread
        """
        item = self.get_item(item_id)
        if not item or "kids" not in item or not item["kids"]:
            return []

        # Use database from context
        db = self.context.db
        if db is None:
            # Create temporary database if needed
            db = CommentDatabase()
            temp_db = True
        else:
            temp_db = False

        new_comments = []

        # Retrieve only top-level comments by their ID
        for kid_id in item["kids"]:
            # Skip if we've already seen this comment
            if db.comment_exists(kid_id):
                continue

            comment_dict = self.get_item(kid_id)
            if not comment_dict:
                continue

            # Skip deleted or dead comments
            if comment_dict.get("deleted") or comment_dict.get("dead"):
                continue

            # Convert to Comment model and add to our list
            comment = Comment(**comment_dict)
            new_comments.append(comment)

            # Store in database
            db.add_comment(comment_dict)

        # Only close the DB connection if we created it
        if temp_db:
            db.close()

        return new_comments

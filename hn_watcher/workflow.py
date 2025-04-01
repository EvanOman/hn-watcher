"""
Workflow module for coordinating HackerNews API operations, database storage,
and message publishing.
"""

from hn_watcher.hn import HackerNewsAPI, HNContext
from hn_watcher.models import Comment


class NewCommentPublisher:
    """
    Coordinates fetching new comments, storing them in the database,
    and publishing them to a message broker.
    """

    def __init__(self, context: HNContext):
        """
        Initialize the comment publisher with a context object.

        Args:
            context: The HN context containing all dependencies
        """
        self.context = context
        self.hn_api = HackerNewsAPI(context)

    def publish_new_comments(self, item_id: int) -> list[Comment]:
        """
        Retrieve only new top-level comments for a given Hacker News item.
        Checks the database to avoid fetching comments we've already seen.
        If a publisher is available, publishes each new comment to the message broker.

        Args:
            item_id: The ID of the HN item (story, poll, etc.)

        Returns:
            A list of only new top-level comments in the thread
        """
        new_comments = self.hn_api.get_new_top_level_comments(item_id)

        # Publish comment if publisher is available
        if self.context.publisher:
            routing_key = f"comment.item.{item_id}"
            for comment in new_comments:
                self.context.publisher.publish_comment(comment, routing_key)

        return new_comments

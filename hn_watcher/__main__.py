#!/usr/bin/env python3
"""
Command-line interface for HN Watcher.
"""

import fire  # type: ignore

from hn_watcher.context import HNContextProvider
from hn_watcher.workflow import NewCommentPublisher


def watch_comments(post_id: int, config_path: str = "") -> None:
    """
    Watch for new comments on a Hacker News post and publish them to RabbitMQ.

    Args:
        post_id: The ID of the Hacker News post
        config_path: Path to the TOML configuration file
    """
    # Create a context using the provider
    context = HNContextProvider.get_default_context(config_path)

    # Create the workflow
    watcher = NewCommentPublisher(context)

    try:
        # Run once and exit
        comments = watcher.publish_new_comments(post_id)
        print(f"Found {len(comments)} new comments")

        for comment in comments:
            print(f"  - {comment.by}: {(comment.text or '')[:50]}...")
    finally:
        # Clean up resources
        context.close()


if __name__ == "__main__":
    fire.Fire(watch_comments)

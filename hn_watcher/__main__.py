from hn_watcher.hn import HackerNewsAPI
from hn_watcher.context import HNContextProvider


def process_comments(post_id: int, context) -> None:
    """
    Process new comments from a Hacker News post.
    
    Args:
        post_id: The ID of the Hacker News post
        context: The HN context to use
    """
    api = HackerNewsAPI(context)
    comments = api.get_new_top_level_comments(post_id)
    
    print(f"Got {len(comments)} comments")

    for comment in comments:
        print(comment['text'])


if __name__ == "__main__":
    # Create a context using the provider
    context = HNContextProvider.get_default_context("hn_comments.db")
    
    # Process comments for a specific post
    process_comments(43485566, context)
    
    # Clean up resources if needed
    if context.db:
        context.db.close()

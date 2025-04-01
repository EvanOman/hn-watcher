from typing import Optional

from pydantic import BaseModel


class Comment(BaseModel):
    """A Hacker News comment."""

    id: int
    parent_id: Optional[int] = None
    by: Optional[str] = None
    time: Optional[int] = None
    text: Optional[str] = None
    deleted: Optional[bool] = False
    dead: Optional[bool] = False

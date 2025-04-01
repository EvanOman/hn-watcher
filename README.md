# HN Watcher

A utility for watching and publishing Hacker News comments.

## Features

- Fetch comments from Hacker News items
- Store comments in a SQLite database
- Publish new comments to RabbitMQ using Avro encoding

## Installation

```bash
pip install -r requirements.txt
```

## Usage Example

Watch for new comments on a Hacker News story and publish them to RabbitMQ:

```bash
python -m hn_watcher 36694815 --db-path=hn_comments.db --rabbit-host=localhost --exchange=hackernews
```

Replace `36694815` with the ID of the Hacker News item you want to watch.

## Development

### Running Tests

Run the tests using pytest:

```bash
# Using pytest directly
pytest

# Or using the justfile
just test

# With coverage
just test-cov
```

### Type Checking

Run mypy type checking:

```bash
just check
```

## Requirements

- Python 3.8+
- RabbitMQ server
- Dependencies listed in pyproject.toml
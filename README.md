# HN Watcher

A systemd service that monitors and stores new comments from Hacker News posts.

## Features

- Monitors specified Hacker News posts for new comments
- Stores comments in a SQLite database to avoid duplicates
- Runs as a systemd service every 15 minutes
- Includes utility scripts for managing and monitoring the service

## Installation

1. Clone this repository
2. Install dependencies: `uv sync`
```
3. Run the setup script to create the systemd service:
```bash
./setup_systemd.sh
```

## Usage

### Managing the Service

Use the `manage_systemd.sh` script to control the service:

```bash
# Check service status
./manage_systemd.sh

# Pause the service
./manage_systemd.sh -p

# Resume the service
./manage_systemd.sh -r

# Show detailed status
./manage_systemd.sh -s
```

### Viewing Logs

Use the `view_hn_watcher_logs.sh` script to check service logs:

```bash
# Show last 50 log entries
./view_hn_watcher_logs.sh

# Follow logs in real-time
./view_hn_watcher_logs.sh -f

# Show last 100 entries
./view_hn_watcher_logs.sh -n 100

# Show logs since a specific time
./view_hn_watcher_logs.sh -s "2 hours ago"
```

## Configuration

The service runs every 15 minutes by default. To modify this, edit the `OnCalendar` setting in `/etc/systemd/system/hn_watcher.timer`.

Comments are stored in `hn_comments.db` using SQLite. The database path can be configured when initializing the `CommentDatabase` class.

## Requirements

- Python 3.10 or higher
- `requests` library
- systemd (Linux)

## License

[Add your license here]

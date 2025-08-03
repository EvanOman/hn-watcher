# sysd - Systemd Service Manager

A clean and modern tool for managing systemd services and timers with abstractions for scheduling.

## Features

- Template-based service/timer generation using Jinja2
- Automatic uv project detection and command wrapping
- Service lifecycle management (add, remove, update)
- Configuration persistence
- Security hardening enabled by default
- Centralized logging to journald
- Easy schedule abstractions (*/15, hourly, daily, @startup, etc.)

## Installation

```bash
# From the sysd directory
pip install -e .

# Or with uv
uv pip install -e .
```

## Usage

```bash
# Add a service
sysd add my-service "python -m my_module" --schedule="*/15" --description="My Service"

# List services
sysd list

# Show service status
sysd status my-service

# View logs
sysd logs my-service --follow

# Remove service
sysd remove my-service
```

## Schedule Formats

- `*/15` - Every 15 minutes
- `hourly`, `daily`, `weekly`, `monthly` - Standard intervals
- `@startup` - On system startup
- `@boot` - On system boot
- Direct systemd calendar syntax

## Testing

```bash
# Run unit tests
pytest

# Run integration tests (requires Docker)
pytest tests/test_integration.py
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run linting
ruff check .
ruff format .

# Run type checking
mypy sysd
```
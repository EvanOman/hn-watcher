# List all available commands
default:
    @just --list

# Install dependencies using uv
install:
    uv sync

# Run the service immediately
run:
    ./scripts/run_hn_watcher_now.sh

# Check service status
status:
    ./scripts/manage_systemd.sh -s

# View logs (last 50 entries)
logs:
    ./scripts/view_hn_watcher_logs.sh

# Follow logs in real-time
logs-follow:
    ./scripts/view_hn_watcher_logs.sh -f

# Pause the service
pause:
    ./scripts/manage_systemd.sh -p

# Resume the service
resume:
    ./scripts/manage_systemd.sh -r

# Setup systemd service and timer
setup:
    ./scripts/setup_systemd.sh

# Run code quality checks
check:
    ruff check --exclude tests .
    ruff format --check --exclude tests .
    uv run mypy hn_watcher

# Format code
fmt:
    ruff check --fix --exclude tests .
    ruff format --exclude tests .
    ruff check --select I --fix

# Clean temporary files
clean:
    rm -rf .ruff_cache/
    rm -rf __pycache__/
    rm -rf *.egg-info/
    rm -rf .pytest_cache/
    rm -rf dist/
    rm -rf build/

# Run unit tests
test:
    uv run pytest

# Run unit tests with coverage
test-cov:
    uv run pytest --cov=hn_watcher tests/

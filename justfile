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

# Setup systemd service and timer (legacy)
setup:
    ./scripts/setup_systemd.sh

# Add a new systemd service (sysd)
add name command schedule="*/15" description="":
    ./bin/sysd add {{name}} "{{command}}" --schedule="{{schedule}}" --description="{{description}}"

# Remove a systemd service (sysd)
remove name:
    ./bin/sysd remove {{name}}

# List all managed systemd services (sysd)
list:
    ./bin/sysd list

# Show service status (sysd)
service-status name="":
    @if [ "{{name}}" = "" ]; then ./bin/sysd status; else ./bin/sysd status {{name}}; fi

# Show service logs (sysd)
service-logs name follow="false":
    @if [ "{{follow}}" = "true" ]; then ./bin/sysd logs {{name}} --follow; else ./bin/sysd logs {{name}}; fi

# Setup HN watcher with new sysd tool
setup-hn-watcher post_id="43858554":
    ./bin/sysd add hn-watcher "python -m hn_watcher {{post_id}}" --schedule="*/15" --description="HN Comment Watcher for post {{post_id}}"

# Test sysd tool
test-sysd:
    cd tools/sysd && ./test.sh

# Test sysd unit tests only
test-sysd-unit:
    cd tools/sysd && pytest tests/test_unit.py -v

# Test sysd integration tests only (requires Docker)
test-sysd-integration:
    cd tools/sysd && pytest tests/test_integration.py -v

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

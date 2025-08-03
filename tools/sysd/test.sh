#!/bin/bash
# Test runner for sysd

set -e

cd "$(dirname "$0")"

echo "=== Running sysd tests ==="

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -f ".venv/bin/activate" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    source .venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]"

# Run unit tests
echo "Running unit tests..."
pytest tests/test_unit.py -v

# Run integration tests if Docker is available
if command -v docker &> /dev/null; then
    echo "Running integration tests..."
    pytest tests/test_integration.py -v --tb=short
else
    echo "Docker not available, skipping integration tests"
fi

# Run linting
echo "Running linting..."
ruff check .
ruff format --check .

# Run type checking
echo "Running type checking..."
mypy sysd

echo "All tests passed!"
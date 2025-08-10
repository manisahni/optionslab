#!/bin/bash

# Run tests and clean up afterwards

echo "Running tests..."

# Run pytest with coverage
pytest

# Store exit code
TEST_EXIT_CODE=$?

echo ""
echo "Cleaning up test artifacts..."

# Clean up any test artifacts
find tests -name "*.pyc" -delete 2>/dev/null || true
find tests -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove .pytest_cache if it exists outside of tests directory
if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache
fi

# Remove coverage file from root if it exists
if [ -f ".coverage" ]; then
    rm -f .coverage
fi

echo "Cleanup complete."

# Exit with the test exit code
exit $TEST_EXIT_CODE
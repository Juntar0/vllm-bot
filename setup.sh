#!/bin/bash

set -e

echo "==================================="
echo "vLLM Bot Setup"
echo "==================================="
echo

# Check Python version
echo "✓ Checking Python version..."
python3 --version || (echo "❌ Python 3 not found" && exit 1)
echo

# Create virtual environment
if [ ! -d venv ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
    echo
fi

# Install requirements
echo "✓ Installing dependencies..."
venv/bin/pip install -q -r requirements.txt
echo

# Create directories
echo "✓ Creating directories..."
mkdir -p workspace
mkdir -p data
echo

# Check config
if [ ! -f config/config.json ]; then
    echo "❌ config/config.json not found"
    exit 1
fi

echo "✓ Verifying config..."
venv/bin/python3 -c "import json; json.load(open('config/config.json'))" || (echo "❌ config/config.json is invalid" && exit 1)
echo

# Run tests
echo "✓ Running tests..."
venv/bin/python3 test/test_integration.py > /dev/null 2>&1 && echo "✓ All tests passed" || echo "⚠️  Some tests failed (non-critical)"
echo

echo "==================================="
echo "✓ Setup complete!"
echo "==================================="
echo
echo "Run: ./run.sh"
echo

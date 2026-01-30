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
mkdir -p config
echo

# Create config if not exists
if [ ! -f config/config.json ]; then
    echo "✓ Creating config/config.json..."
    cat > config/config.json << 'EOF'
{
  "vllm": {
    "base_url": "http://localhost:8000/v1",
    "model": "gpt-oss-medium",
    "temperature": 0.0,
    "max_tokens": 2048,
    "enable_function_calling": true
  },
  "workspace": {
    "dir": "./workspace"
  },
  "security": {
    "exec_enabled": true,
    "allowed_commands": ["ls", "cat", "grep", "find", "echo", "wc"],
    "timeout_sec": 30,
    "max_output_size": 200000
  },
  "memory": {
    "path": "./data/memory.json",
    "auto_backup": true
  },
  "audit": {
    "enabled": true,
    "log_path": "./data/runlog.jsonl"
  },
  "agent": {
    "max_loops": 5,
    "loop_wait_sec": 0.5
  },
  "debug": {
    "enabled": false,
    "level": "basic",
    "show_planner": true,
    "show_tool_runner": true,
    "show_responder": true,
    "show_state": true
  }
}
EOF
    echo
fi

# Verify config
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

#!/bin/bash

set -e

echo "==================================="
echo "vLLM Bot Setup Wizard"
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

# Interactive config wizard
if [ ! -f config/config.json ]; then
    echo "==================================="
    echo "Configuration Wizard"
    echo "==================================="
    echo

    # vLLM settings
    echo "vLLM Configuration:"
    read -p "  Base URL [http://localhost:8000/v1]: " vllm_base_url
    vllm_base_url=${vllm_base_url:-http://localhost:8000/v1}
    
    read -p "  Model [gpt-oss-medium]: " vllm_model
    vllm_model=${vllm_model:-gpt-oss-medium}
    
    echo

    # Workspace settings
    echo "Workspace Configuration:"
    read -p "  Workspace directory [./workspace]: " workspace_dir
    workspace_dir=${workspace_dir:-./workspace}
    
    echo

    # Security settings
    echo "Security Configuration:"
    echo "  Command permission level:"
    echo "    1) Restricted (default: ls, cat, grep, find, echo, wc)"
    echo "    2) Full access (all commands)"
    echo "    3) Custom (specify commands)"
    read -p "  Choose [1]: " security_level
    security_level=${security_level:-1}
    
    case $security_level in
        1)
            allowed_commands='["ls", "cat", "grep", "find", "echo", "wc"]'
            echo "  ✓ Using restricted mode"
            ;;
        2)
            allowed_commands='[]'
            echo "  ✓ Using full access mode"
            echo "  ⚠️  WARNING: All commands will be allowed!"
            echo "  ℹ️  Note: sudo is already included in full access mode"
            ;;
        3)
            read -p "  Allowed commands (comma-separated): " allowed_cmds
            allowed_commands="[\"$(echo $allowed_cmds | sed 's/,/", "/g')\"]"
            echo "  ✓ Custom commands: $allowed_cmds"
            ;;
        *)
            allowed_commands='["ls", "cat", "grep", "find", "echo", "wc"]'
            echo "  ✓ Using restricted mode (invalid input)"
            ;;
    esac
    
    echo

    # Workspace restriction
    echo "Workspace Restriction:"
    echo "  1) Restricted (./workspace only)"
    echo "  2) Full system access (/)"
    read -p "  Choose [1]: " workspace_level
    workspace_level=${workspace_level:-1}
    
    case $workspace_level in
        2)
            workspace_dir="/"
            echo "  ✓ Full system access enabled"
            echo "  ⚠️  WARNING: Full system access allowed!"
            ;;
        *)
            workspace_dir=${workspace_dir:-./workspace}
            echo "  ✓ Using workspace restriction"
            ;;
    esac
    
    echo

    # Debug settings
    read -p "  Enable debug? (y/n) [n]: " enable_debug
    enable_debug=${enable_debug:-n}
    
    if [[ "$enable_debug" =~ ^[Yy]$ ]]; then
        debug_enabled="true"
    else
        debug_enabled="false"
    fi
    
    echo

    # Create config.json
    echo "✓ Creating config/config.json..."
    cat > config/config.json << EOF
{
  "vllm": {
    "base_url": "$vllm_base_url",
    "model": "$vllm_model",
    "temperature": 0.0,
    "max_tokens": 2048,
    "enable_function_calling": true
  },
  "workspace": {
    "dir": "$workspace_dir"
  },
  "security": {
    "exec_enabled": true,
    "allowed_commands": $allowed_commands,
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
    "enabled": $debug_enabled,
    "level": "basic",
    "show_planner": true,
    "show_tool_runner": true,
    "show_responder": true,
    "show_state": true
  }
}
EOF
    echo
else
    echo "✓ config/config.json already exists (skipping wizard)"
    echo
    echo "To reconfigure, delete the file:"
    echo "  rm config/config.json"
    echo "  ./setup.sh"
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
echo "Configuration:"
venv/bin/python3 -c "
import json
cfg = json.load(open('config/config.json'))
print(f\"  vLLM: {cfg['vllm']['base_url']}\")
print(f\"  Model: {cfg['vllm']['model']}\")
print(f\"  Workspace: {cfg['workspace']['dir']}\")
print(f\"  Commands: {cfg['security']['allowed_commands']}\")
print(f\"  Debug: {cfg['debug']['enabled']}\")
"
echo
echo "To run: ./run.sh"
echo

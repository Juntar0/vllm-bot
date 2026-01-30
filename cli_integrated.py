#!/usr/bin/env python3
"""
vLLM Bot - Integrated CLI
Full agent with Planner-ToolRunner-Responder architecture
"""

import json
import sys
from pathlib import Path
from src.agent import Agent


def load_config(config_path: str = None) -> dict:
    """Load configuration from JSON file"""
    
    if not config_path:
        config_path = './config/config.json'
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)


def print_welcome():
    """Print welcome message"""
    print("\n" + "=" * 80)
    print("vLLM Bot - Integrated Agent")
    print("=" * 80)
    print()
    print("Architecture: Planner → ToolRunner → Responder (max 5 loops)")
    print()


def main():
    """Main CLI entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python3 cli_integrated.py <request>")
        print()
        print("Example:")
        print('  python3 cli_integrated.py "List all Python files"')
        print()
        print("Configuration: Edit config/config.json to change settings")
        print('  python3 cli_integrated.py "Find and count lines" ./config/custom.json')
        sys.exit(1)
    
    user_request = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print_welcome()
    
    # Load config
    print("Loading configuration...")
    config = load_config(config_path)
    print(f"✓ Loaded config from {config_path or './config/config.json'}")
    print()
    
    # Initialize agent
    print("Initializing agent...")
    try:
        agent = Agent(config)
        print("✓ Agent initialized")
        print(f"  - Model: {config['vllm']['model']}")
        print(f"  - Workspace: {config['workspace']['dir']}")
        print(f"  - Max loops: {config['agent']['max_loops']}")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        sys.exit(1)
    
    # Run agent
    print(f"📝 User Request: {user_request}")
    print()
    print("=" * 80)
    print("Executing agent loop...")
    print("=" * 80)
    print()
    
    try:
        response = agent.run(user_request)
    except Exception as e:
        print(f"❌ Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Print response
    print()
    print("=" * 80)
    print("AGENT RESPONSE")
    print("=" * 80)
    print()
    print(response)
    print()
    
    # Print summary
    agent.print_summary()
    
    # Print audit log summary if available
    audit_summary = agent.get_audit_log_summary()
    if audit_summary:
        print()
        print("=" * 80)
        print("AUDIT LOG SUMMARY")
        print("=" * 80)
        print(audit_summary)
    
    # Save memory
    print()
    print("Saving memory...")
    agent.save_memory()
    print("✓ Memory saved")
    print()


if __name__ == '__main__':
    main()

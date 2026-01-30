#!/usr/bin/env python3
"""
vLLM Bot - Interactive Chat Interface
Multi-turn conversation with memory and context
"""

import json
import sys
from pathlib import Path
from src.agent import Agent


def load_config(config_path: str = 'config/config.json') -> dict:
    """Load configuration from JSON file"""
    
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
    print("vLLM Bot - Interactive Agent")
    print("=" * 80)
    print()
    print("Type your request and press Enter.")
    print("Type 'exit' or 'quit' to exit.")
    print("Type 'help' for commands.")
    print()


def print_help():
    """Print help message"""
    print()
    print("Commands:")
    print("  help          - Show this help")
    print("  clear         - Clear conversation history")
    print("  debug on      - Enable debug output")
    print("  debug off     - Disable debug output")
    print("  config        - Show current config")
    print("  exit / quit   - Exit the agent")
    print()


def print_config(config: dict):
    """Print relevant config"""
    print()
    print("Current Configuration:")
    print(f"  Model: {config['vllm']['model']}")
    print(f"  Workspace: {config['workspace']['dir']}")
    print(f"  Max loops: {config['agent']['max_loops']}")
    print(f"  Debug: {config['debug']['enabled']}")
    print()


def main():
    """Main interactive CLI loop"""
    
    # Load configuration
    config = load_config()
    
    print_welcome()
    
    # Initialize agent
    print("Initializing agent...")
    try:
        agent = Agent(config)
        print("✓ Agent ready")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        sys.exit(1)
    
    # Interactive loop
    conversation_count = 0
    
    while True:
        try:
            # Get user input
            user_input = input("> ").strip()
            
            # Handle empty input
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == 'exit' or user_input.lower() == 'quit':
                print("\nGoodbye! 👋")
                break
            
            if user_input.lower() == 'help':
                print_help()
                continue
            
            if user_input.lower() == 'clear':
                # Reset agent for new conversation
                agent = Agent(config)
                conversation_count = 0
                print("✓ Conversation cleared")
                print()
                continue
            
            if user_input.lower() == 'config':
                print_config(config)
                continue
            
            if user_input.lower().startswith('debug'):
                parts = user_input.split()
                if len(parts) >= 2:
                    if parts[1].lower() == 'on':
                        config['debug']['enabled'] = True
                        agent.debugger.enabled = True
                        print("✓ Debug enabled")
                    elif parts[1].lower() == 'off':
                        config['debug']['enabled'] = False
                        agent.debugger.enabled = False
                        print("✓ Debug disabled")
                print()
                continue
            
            # Process user request
            conversation_count += 1
            
            print()
            
            try:
                response = agent.run(user_input)
                print(response)
                print()
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
        
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            print()


if __name__ == '__main__':
    main()

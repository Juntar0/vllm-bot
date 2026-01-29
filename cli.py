#!/usr/bin/env python3
"""
vLLM Bot - CLI Interface
"""
import sys
import json
from pathlib import Path
from src.agent import Agent


class CLIBot:
    def __init__(self, agent: Agent, debug: bool = False):
        self.agent = agent
        self.user_id = 1  # Fixed user ID for CLI
        self.debug = debug
        
    def print_welcome(self):
        """
        Print welcome message
        """
        print("=" * 60)
        print("🤖 vLLM Bot - CLI Interface")
        print("=" * 60)
        print()
        print("Available commands:")
        print("  /reset    - Reset conversation history")
        print("  /help     - Show this help")
        print("  /exit     - Exit the bot")
        print()
        print("Available tools:")
        print("  - read(path, offset?, limit?)")
        print("  - write(path, content)")
        print("  - edit(path, oldText, newText)")
        print("  - exec(command)")
        print()
        print("=" * 60)
        print()
    
    def print_help(self):
        """
        Print help message
        """
        print()
        print("📖 Help:")
        print()
        print("To use tools, the AI will output:")
        print("  TOOL_CALL: { \"name\": \"read\", \"args\": { \"path\": \"file.txt\" } }")
        print()
        print("Examples:")
        print("  You: List files in the workspace")
        print("  Bot: TOOL_CALL: { \"name\": \"exec\", \"args\": { \"command\": \"ls -la\" } }")
        print()
        print("  You: Read README.md")
        print("  Bot: TOOL_CALL: { \"name\": \"read\", \"args\": { \"path\": \"README.md\" } }")
        print()
    
    def run(self):
        """
        Run CLI REPL
        """
        self.print_welcome()
        
        while True:
            try:
                # Prompt
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input == "/exit":
                    print("\n👋 Goodbye!")
                    break
                
                if user_input == "/reset":
                    self.agent.reset_conversation(self.user_id)
                    print("✅ Conversation history reset!\n")
                    continue
                
                if user_input == "/help":
                    self.print_help()
                    continue
                
                # Get response from agent
                print()
                print("Bot: ", end="", flush=True)
                
                response = self.agent.chat(self.user_id, user_input, debug=self.debug)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


def select_model(config):
    """
    Prompt user to select a model from config
    """
    vllm_config = config.get("vllm", {})
    models = vllm_config.get("available_models", ["gpt-oss-medium"])
    default_index = vllm_config.get("default_model_index", 0)
    
    # Validate default_index
    if default_index < 0 or default_index >= len(models):
        default_index = 0
    
    print("Available models:")
    for i, model in enumerate(models, 1):
        default_marker = " (default)" if i - 1 == default_index else ""
        print(f"  {i}. {model}{default_marker}")
    print()
    
    while True:
        try:
            prompt = f"Select model (1-{len(models)}) [default: {default_index + 1}]: "
            choice = input(prompt).strip()
            
            if not choice:
                return models[default_index]
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(models):
                return models[choice_num - 1]
            else:
                print(f"Invalid choice. Please enter 1-{len(models)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)


def load_config(config_path: str = "config/config.json") -> dict:
    """
    Load configuration file
    """
    path = Path(config_path)
    
    if not path.exists():
        print(f"❌ Config file not found: {config_path}")
        print("💡 Copy config/config.example.json to config/config.json and fill in your settings")
        sys.exit(1)
    
    with open(path, 'r') as f:
        return json.load(f)


def main():
    """
    Main entry point
    """
    print("🚀 Starting vLLM Bot (CLI)...\n")
    
    # Load configuration
    config = load_config()
    
    # Validate vLLM config
    if not config.get("vllm", {}).get("base_url"):
        print("❌ vLLM base_url not configured")
        sys.exit(1)
    
    # Select model
    selected_model = select_model(config)
    print(f"\n✅ Selected model: {selected_model}\n")
    
    # Override model in config
    config["vllm"]["model"] = selected_model
    config["vllm"]["api_key"] = "dummy"  # Force dummy token
    
    # Create agent
    print("🤖 Initializing agent...")
    agent = Agent(
        vllm_config=config["vllm"],
        workspace_config=config["workspace"],
        security_config=config["security"],
        system_prompt_config=config["system_prompt"]
    )
    
    # Create and run CLI bot
    print("✅ Ready!\n")
    
    # Check for debug mode
    import os
    debug = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
    if debug:
        print("🐛 Debug mode enabled\n")
    
    bot = CLIBot(agent, debug=debug)
    bot.run()


if __name__ == "__main__":
    main()

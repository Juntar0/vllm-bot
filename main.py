#!/usr/bin/env python3
"""
vLLM Bot - Main Entry Point
"""
import json
import sys
from pathlib import Path
from src.agent import Agent
from src.telegram_bot import TelegramBot


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
    print("🚀 Starting vLLM Bot...")
    
    # Load configuration
    config = load_config()
    
    # Validate required fields
    if not config.get("telegram", {}).get("token"):
        print("❌ Telegram token not configured")
        sys.exit(1)
    
    if not config.get("vllm", {}).get("base_url"):
        print("❌ vLLM base_url not configured")
        sys.exit(1)
    
    # Create agent
    print("🤖 Initializing agent...")
    agent = Agent(
        vllm_config=config["vllm"],
        workspace_config=config["workspace"],
        security_config=config["security"],
        system_prompt_config=config["system_prompt"]
    )
    
    # Create and run Telegram bot
    print("📱 Initializing Telegram bot...")
    bot = TelegramBot(
        token=config["telegram"]["token"],
        agent=agent,
        allowed_users=config["telegram"].get("allowed_users")
    )
    
    print("✅ Ready!")
    bot.run()


if __name__ == "__main__":
    main()

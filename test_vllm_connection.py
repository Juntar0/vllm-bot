#!/usr/bin/env python3
"""
Test vLLM Connection
"""
import json
import sys
import requests
from pathlib import Path


def load_config():
    """Load config.json"""
    config_path = Path("config/config.json")
    
    if not config_path.exists():
        print("❌ config/config.json not found")
        print("💡 Run: cp config/config.cli.json config/config.json")
        return None
    
    with open(config_path) as f:
        return json.load(f)


def test_connection(base_url, model):
    """Test vLLM API connection"""
    url = f"{base_url.rstrip('/')}/chat/completions"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello! Say hi in one word."}
        ],
        "max_tokens": 10
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer dummy"
    }
    
    try:
        print(f"📡 Testing connection to: {url}")
        print(f"🤖 Model: {model}")
        print()
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        message = data["choices"][0]["message"]["content"]
        
        print("✅ Connection successful!")
        print(f"📝 Response: {message}")
        print()
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed: Cannot reach vLLM server")
        print(f"💡 Make sure vLLM is running at {base_url}")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ Connection timeout")
        return False
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        if response.status_code == 404:
            print(f"💡 Model '{model}' not found on server")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("🧪 vLLM Connection Test")
    print("=" * 50)
    print()
    
    config = load_config()
    if not config:
        sys.exit(1)
    
    vllm_config = config.get("vllm", {})
    base_url = vllm_config.get("base_url")
    
    if not base_url:
        print("❌ vllm.base_url not configured")
        sys.exit(1)
    
    # Get available models from config
    models = vllm_config.get("available_models", ["gpt-oss-medium"])
    
    print(f"Testing {len(models)} available model(s):")
    print()
    
    results = {}
    for model in models:
        print(f"--- {model} ---")
        results[model] = test_connection(base_url, model)
        print()
    
    # Summary
    print("=" * 50)
    print("📊 Summary:")
    print()
    for model, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {model}")
    print()
    
    if all(results.values()):
        print("🎉 All models are accessible!")
        print("✅ You can now run: python cli.py")
    else:
        print("⚠️  Some models are not accessible")
        print("💡 Check vLLM server configuration")


if __name__ == "__main__":
    main()

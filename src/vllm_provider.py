"""
vLLM Provider - OpenAI Compatible API
"""
import json
import requests
from typing import List, Dict, Any, Optional, Iterator


class VLLMProvider:
    def __init__(self, config: Dict[str, Any], debugger=None):
        self.base_url = config["base_url"].rstrip("/")
        self.model = config["model"]
        self.api_key = config.get("api_key", "dummy")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)
        self.debugger = debugger
        
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Call vLLM chat completion API
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream
        }
        
        # Add tools if provided (some vLLM models support function calling)
        if tools:
            payload["tools"] = tools
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Debug: Show API request
        if self.debugger:
            self.debugger.print("VLLM_API", f"--- API Request ---")
            self.debugger.print("VLLM_API", f"URL: {url}")
            self.debugger.print("VLLM_API", f"Model: {self.model}")
            self.debugger.print("VLLM_API", f"Temperature: {self.temperature}")
            self.debugger.print("VLLM_API", f"Max Tokens: {self.max_tokens}")
            self.debugger.print("VLLM_API", f"Messages ({len(messages)}):")
            for i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                content_preview = content[:150] + "..." if len(content) > 150 else content
                self.debugger.print("VLLM_API", f"  [{i}] {role}: {content_preview}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, stream=stream)
            response.raise_for_status()
            
            if stream:
                result = self._handle_stream(response)
            else:
                result = response.json()
            
            # Debug: Show API response
            if self.debugger:
                self.debugger.print("VLLM_API", f"--- API Response ---")
                if isinstance(result, dict) and "choices" in result:
                    choices = result.get("choices", [])
                    if choices:
                        choice = choices[0]
                        finish_reason = choice.get("finish_reason", "unknown")
                        message = choice.get("message", {})
                        content = message.get("content", "")
                        content_preview = content[:150] + "..." if len(content) > 150 else content
                        self.debugger.print("VLLM_API", f"Finish Reason: {finish_reason}")
                        self.debugger.print("VLLM_API", f"Response: {content_preview}")
            
            return result
                
        except requests.RequestException as e:
            if self.debugger:
                self.debugger.print("VLLM_API", f"✗ Error: {str(e)}")
            raise Exception(f"vLLM API error: {str(e)}")
    
    def _handle_stream(self, response) -> Iterator[Dict[str, Any]]:
        """
        Handle streaming response
        """
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data_str = line_str[6:]  # Remove "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        yield data
                    except json.JSONDecodeError:
                        continue
    
    def extract_message(self, response: Dict[str, Any]) -> str:
        """
        Extract message content from response
        """
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise Exception("Invalid response format")
    
    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response (if model supports function calling)
        """
        try:
            message = response["choices"][0]["message"]
            return message.get("tool_calls", [])
        except (KeyError, IndexError):
            return []

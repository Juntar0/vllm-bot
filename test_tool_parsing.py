#!/usr/bin/env python3
"""
Test tool call parsing
"""
import json
import re
from typing import List, Dict, Any, Optional


def _extract_json_object(text: str, start: int) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object using brace counting (more robust)
    """
    if start >= len(text) or text[start] != '{':
        return None
    
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start, len(text)):
        char = text[i]
        
        if escape:
            escape = False
            continue
        
        if char == '\\':
            escape = True
            continue
        
        if char == '"':
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_str = text[start:i+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return None
    
    return None


def _parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    """
    Parse tool calls from text (simple regex-based for non-function-calling models)
    """
    tool_calls = []
    
    # Match: TOOL_CALL: { ... }
    # Use more flexible pattern to handle nested objects and multiline JSON
    pattern = r'TOOL_CALL:\s*(\{(?:[^{}]|\{[^{}]*\})*\})'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            json_str = match.group(1)
            tool_call = json.loads(json_str)
            if "name" in tool_call and "args" in tool_call:
                tool_calls.append(tool_call)
        except json.JSONDecodeError:
            # Try to extract with simple brace matching
            try:
                tool_call = _extract_json_object(text, match.start(1))
                if tool_call and "name" in tool_call and "args" in tool_call:
                    tool_calls.append(tool_call)
            except:
                continue
    
    return tool_calls


# Test cases
test_cases = [
    # Case 1: Simple single line
    'TOOL_CALL: {"name": "exec", "args": {"command": "ls"}}',
    
    # Case 2: Multiline
    '''TOOL_CALL: {
  "name": "exec",
  "args": {
    "command": "ls -R ."
  }
}''',
    
    # Case 3: With extra text
    '''Sure, I'll list the files for you.

TOOL_CALL: {
  "name": "exec",
  "args": { "command": "ls -la" }
}

Let me check that for you.''',
    
    # Case 4: Multiple tool calls
    '''TOOL_CALL: {"name": "read", "args": {"path": "file.txt"}}

And then:

TOOL_CALL: {"name": "exec", "args": {"command": "pwd"}}''',
]

print("Testing tool call parsing...\n")

for i, test in enumerate(test_cases, 1):
    print(f"Test Case {i}:")
    print("=" * 60)
    print("Input:")
    print(test)
    print("\nParsed:")
    result = _parse_tool_calls(test)
    print(json.dumps(result, indent=2))
    print("\n")

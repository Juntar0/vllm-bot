"""
Agent - Orchestrates LLM and tool execution
"""
import json
import re
from typing import List, Dict, Any, Optional
from .vllm_provider import VLLMProvider
from .tools import ToolExecutor, TOOL_DEFINITIONS


class Agent:
    def __init__(self, vllm_config: Dict[str, Any], workspace_config: Dict[str, Any], 
                 security_config: Dict[str, Any], system_prompt_config: Dict[str, Any]):
        self.vllm = VLLMProvider(vllm_config)
        self.tools = ToolExecutor(workspace_config["dir"], security_config)
        self.system_prompt_config = system_prompt_config
        self.workspace_dir = workspace_config["dir"]
        self.enable_function_calling = vllm_config.get("enable_function_calling", True)
        
        # Conversation history per user
        self.conversations: Dict[int, List[Dict[str, str]]] = {}
        
    def _build_system_prompt(self) -> str:
        """
        Build system prompt dynamically (inspired by Clawdbot)
        """
        lines = []
        
        # Role
        lines.append(self.system_prompt_config.get("role", "You are a helpful assistant."))
        lines.append("")
        
        # Workspace
        workspace_note = self.system_prompt_config.get("workspace_note", "")
        if workspace_note:
            lines.append(workspace_note.format(workspace_dir=self.workspace_dir))
            lines.append("")
        
        # Tools - Generate from TOOL_DEFINITIONS dynamically
        tools_note = self.system_prompt_config.get("tools_note", "")
        if tools_note:
            lines.append("## Available Tools")
            lines.append("")
            
            # Generate tool descriptions from TOOL_DEFINITIONS
            for tool_def in TOOL_DEFINITIONS:
                func = tool_def["function"]
                name = func["name"]
                desc = func["description"]
                params = func["parameters"]["properties"]
                required = func["parameters"].get("required", [])
                
                # Build parameter list
                param_list = []
                for param_name, param_info in params.items():
                    is_required = param_name in required
                    param_str = param_name if is_required else f"{param_name}?"
                    param_list.append(param_str)
                
                # Format: - **tool_name(param1, param2?)**: Description
                lines.append(f"- **{name}({', '.join(param_list)})**: {desc}")
            
            lines.append("")
            lines.append("## Tool Call Format")
            lines.append("")
            lines.append("To call a tool, use this exact format:")
            lines.append("```")
            lines.append("TOOL_CALL: {")
            lines.append('  "name": "tool_name",')
            lines.append('  "args": { ... }')
            lines.append("}")
            lines.append("```")
            lines.append("")
            lines.append("Example:")
            lines.append("```")
            lines.append("TOOL_CALL: {")
            lines.append('  "name": "read",')
            lines.append('  "args": { "path": "README.md" }')
            lines.append("}")
            lines.append("```")
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_conversation(self, user_id: int) -> List[Dict[str, str]]:
        """
        Get or create conversation history for user
        """
        if user_id not in self.conversations:
            self.conversations[user_id] = [
                {"role": "system", "content": self._build_system_prompt()}
            ]
        return self.conversations[user_id]
    
    def _parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
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
                    tool_call = self._extract_json_object(text, match.start(1))
                    if tool_call and "name" in tool_call and "args" in tool_call:
                        tool_calls.append(tool_call)
                except:
                    continue
        
        return tool_calls
    
    def _extract_json_object(self, text: str, start: int) -> Optional[Dict[str, Any]]:
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
    
    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute tool calls and return results
        """
        results = []
        for call in tool_calls:
            name = call["name"]
            args = call["args"]
            result = self.tools.execute(name, args)
            results.append({
                "name": name,
                "args": args,
                "result": result
            })
        return results
    
    def chat(self, user_id: int, message: str, max_iterations: int = 5, debug: bool = False) -> str:
        """
        Handle chat message with tool execution loop
        """
        conversation = self._get_conversation(user_id)
        
        # Add user message
        conversation.append({"role": "user", "content": message})
        
        # Agentic loop (allow multiple tool calls)
        for iteration in range(max_iterations):
            try:
                # Call vLLM (with tools if function calling enabled)
                tools_param = TOOL_DEFINITIONS if self.enable_function_calling else None
                response = self.vllm.chat_completion(conversation, tools=tools_param)
                assistant_message = self.vllm.extract_message(response)
                
                # Check if model returned function calls (OpenAI format)
                if self.enable_function_calling:
                    function_tool_calls = self.vllm.extract_tool_calls(response)
                    if function_tool_calls:
                        # Model used native function calling, convert to our format
                        tool_calls = []
                        for fc in function_tool_calls:
                            tool_calls.append({
                                "name": fc["function"]["name"],
                                "args": json.loads(fc["function"]["arguments"])
                            })
                        if debug:
                            print(f"[DEBUG] Function calling format detected: {len(tool_calls)} calls")
                    else:
                        # Fallback to text-based parsing
                        tool_calls = self._parse_tool_calls(assistant_message)
                else:
                    # Function calling disabled, use text-based parsing only
                    tool_calls = self._parse_tool_calls(assistant_message)
                
                # Check for tool calls (text-based parsing)
                tool_calls = self._parse_tool_calls(assistant_message)
                
                if debug:
                    print(f"\n[DEBUG] Iteration {iteration + 1}")
                    print(f"[DEBUG] Tool calls found: {len(tool_calls)}")
                    if tool_calls:
                        print(f"[DEBUG] Tool calls: {tool_calls}")
                
                if not tool_calls:
                    # No tool calls - return response
                    conversation.append({"role": "assistant", "content": assistant_message})
                    return assistant_message
                
                # Execute tools
                tool_results = self._execute_tools(tool_calls)
                
                # Build tool result message
                result_lines = []
                result_lines.append("Tool execution results:")
                result_lines.append("")
                for i, tr in enumerate(tool_results, 1):
                    result_lines.append(f"**{i}. {tr['name']}**")
                    result_lines.append(f"Args: {json.dumps(tr['args'])}")
                    if "error" in tr["result"]:
                        result_lines.append(f"Error: {tr['result']['error']}")
                    else:
                        result_lines.append(f"Result: {tr['result'].get('result', str(tr['result']))}")
                    result_lines.append("")
                
                tool_result_text = "\n".join(result_lines)
                
                # Add assistant message + tool results to conversation
                conversation.append({"role": "assistant", "content": assistant_message})
                conversation.append({"role": "user", "content": tool_result_text})
                
                # Continue loop for next iteration
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                conversation.append({"role": "assistant", "content": error_msg})
                return error_msg
        
        # Max iterations reached
        final_msg = "Reached maximum tool execution iterations. Please try a simpler request."
        conversation.append({"role": "assistant", "content": final_msg})
        return final_msg
    
    def reset_conversation(self, user_id: int):
        """
        Reset conversation history for user
        """
        if user_id in self.conversations:
            del self.conversations[user_id]

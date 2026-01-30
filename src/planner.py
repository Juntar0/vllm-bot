"""
Planner - Tool selection and planning LLM
Decides what tools to call next based on user request, memory, and state
"""

import json
import re
from typing import Optional, Dict, Any, List
from src.vllm_provider import VLLMProvider
from src.memory import Memory
from src.state import AgentState, PlannerOutput, ToolCall
from src.audit_log import AuditLog


class Planner(VLLMProvider):
    """
    Planner LLM - Decides which tools to call next
    
    Responsibilities:
    - Analyze user request + memory + state
    - Decide which tools to call (or if no tools needed)
    - Output strictly formatted JSON
    - Prevent infinite loops and repeated failures
    
    Input:
    - System instructions + TOOL specs
    - MEMORY (user preferences, environment, decisions)
    - STATE (loop history, facts, remaining tasks)
    - User request
    
    Output:
    - JSON with tool_calls, reason_brief, stop_condition
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        memory: Memory,
        state: AgentState,
        audit_log: Optional[AuditLog] = None,
        debugger = None
    ):
        """
        Initialize Planner
        
        Args:
            config: vLLM config dict with base_url, model, etc.
            memory: Memory instance
            state: AgentState instance
            audit_log: Optional AuditLog instance
            debugger: Optional Debugger instance
        """
        super().__init__(config, debugger)
        
        self.memory = memory
        self.state = state
        self.audit_log = audit_log
        self.enable_function_calling = config.get('enable_function_calling', True)
        
        # Available tools specification
        self.tool_specs = self._build_tool_specs()
    
    def plan(
        self,
        user_request: str,
        available_tools: List[str] = None
    ) -> PlannerOutput:
        """
        Generate a plan for the next step
        
        Args:
            user_request: The user's original request
            available_tools: List of available tool names (optional filter)
        
        Returns:
            PlannerOutput with tool_calls and reasoning
        """
        
        # Build system prompt
        system_prompt = self._build_system_prompt(user_request, available_tools)
        
        # Create messages list for chat completion
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate a plan by responding with valid JSON."}
        ]
        
        # Call LLM
        try:
            response = self.chat_completion(messages)
        except Exception as e:
            if self.audit_log:
                self.audit_log.log_error(
                    loop_id=self.state.loop_count,
                    error_type='PlannerLLMError',
                    error_message=str(e),
                    context={'user_request': user_request}
                )
            raise
        
        # Extract text from response
        if isinstance(response, dict):
            # Handle structured response from API
            choices = response.get('choices', [])
            if choices and isinstance(choices[0], dict):
                response_text = choices[0].get('message', {}).get('content', '')
            else:
                response_text = str(response)
        else:
            response_text = str(response)
        
        # Parse output
        output = self._parse_planner_output(response_text)
        
        # Log decision
        if self.audit_log:
            self.audit_log.log_planner_decision(
                loop_id=self.state.loop_count,
                decision={
                    'need_tools': output.need_tools,
                    'tool_calls': [tc.to_dict() for tc in output.tool_calls]
                },
                reasoning=output.reason_brief
            )
        
        return output
    
    def _build_system_prompt(
        self,
        user_request: str,
        available_tools: Optional[List[str]] = None
    ) -> str:
        """
        Build the system prompt for the Planner
        
        Includes:
        1. Instructions
        2. Available tools
        3. MEMORY context
        4. STATE summary
        5. User request
        """
        
        system_instruction = """You are a planning agent for an OS automation system.

Your role is to decide what tools to call next based on:
1. The user's request
2. Your long-term memory (preferences, environment, decisions)
3. The current state (facts gathered, tasks remaining, loop history)

Output MUST be valid JSON with this exact structure:
{
  "need_tools": boolean,
  "tool_calls": [
    {"tool_name": "...", "args": {...}},
    ...
  ],
  "reason_brief": "string (max 300 chars)",
  "stop_condition": "string - what signals completion?"
}

RULES:
1. If no tools needed (e.g., can answer from memory), set need_tools=false and leave tool_calls empty
2. Only call tools that are available (see list below)
3. Prevent infinite loops: check history, don't repeat same calls
4. Be concise in reason_brief
5. Always output valid JSON, never include explanations outside JSON

FORBIDDEN:
- Making assumptions beyond what tools return
- Suggesting destructive operations without explicit user consent
- Calling tools in wrong order (dependencies matter)
"""
        
        tools_section = f"""Available Tools:
{self.tool_specs}

Filtered by: {', '.join(available_tools) if available_tools else 'all tools available'}
"""
        
        memory_section = f"""Long-term Memory (preferences, environment, repeated decisions):
{self.memory.to_context()}
"""
        
        state_section = f"""Current State (loop progress, facts, remaining tasks):
{self.state.to_context()}

Loop History (recent 3):
{self.state.get_history_summary(max_loops=3)}
"""
        
        user_section = f"""User Request (original):
{user_request}

Current Goal: {self.state.remaining_tasks[0] if self.state.remaining_tasks else 'Complete the request'}
"""
        
        return f"""{system_instruction}

{tools_section}

{memory_section}

{state_section}

{user_section}

Output your JSON response:
"""
    
    def _build_tool_specs(self) -> str:
        """
        Build specification of available tools
        
        Returns:
            Formatted string describing each tool
        """
        
        tools = [
            {
                'name': 'list_dir',
                'description': 'List files and directories',
                'args': {
                    'path': 'Directory path (default: current workspace)'
                }
            },
            {
                'name': 'read_file',
                'description': 'Read file contents',
                'args': {
                    'path': 'File path',
                    'offset': 'Optional: starting line number',
                    'limit': 'Optional: maximum lines to read'
                }
            },
            {
                'name': 'write_file',
                'description': 'Write or create a file',
                'args': {
                    'path': 'File path',
                    'content': 'Content to write'
                }
            },
            {
                'name': 'edit_file',
                'description': 'Edit a file by replacing text',
                'args': {
                    'path': 'File path',
                    'oldText': 'Text to find (must appear exactly once)',
                    'newText': 'Text to replace with'
                }
            },
            {
                'name': 'exec_cmd',
                'description': 'Execute a shell command',
                'args': {
                    'command': 'Shell command to execute',
                    'timeout': 'Optional: timeout in seconds'
                }
            },
            {
                'name': 'grep',
                'description': 'Search for text in files',
                'args': {
                    'pattern': 'Text pattern to search',
                    'path': 'File or directory path'
                }
            },
        ]
        
        specs = []
        for i, tool in enumerate(tools, 1):
            spec = f"""{i}. {tool['name']}
   Description: {tool['description']}
   Args: {json.dumps(tool['args'], ensure_ascii=False)}"""
            specs.append(spec)
        
        return '\n'.join(specs)
    
    def _parse_planner_output(self, response: str) -> PlannerOutput:
        """
        Parse and validate Planner's JSON output
        
        Args:
            response: Raw response from LLM
        
        Returns:
            Validated PlannerOutput object
        
        Raises:
            ValueError: If response is not valid JSON
        """
        
        # Try to extract JSON from response
        json_str = self._extract_json(response)
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Detailed error message for debugging
            error_msg = f"Invalid JSON from Planner: {e}\nResponse: {response[:500]}"
            if self.debugger:
                self.debugger.print("PLANNER", f"--- JSON Parse Error ---")
                self.debugger.print("PLANNER", f"Error: {str(e)}")
                self.debugger.print("PLANNER", f"Raw response: {response[:500]}")
                self.debugger.print("PLANNER", f"Extracted JSON: {json_str[:200]}")
            raise ValueError(error_msg)
        
        # Validate required fields
        if 'need_tools' not in data:
            raise ValueError("Missing 'need_tools' field in Planner output")
        
        need_tools = data.get('need_tools', False)
        tool_calls = []
        
        if need_tools:
            # Parse tool calls
            raw_calls = data.get('tool_calls', [])
            
            if not isinstance(raw_calls, list):
                raise ValueError("'tool_calls' must be a list")
            
            for call_data in raw_calls:
                if not isinstance(call_data, dict):
                    raise ValueError("Each tool call must be a dictionary")
                
                tool_name = call_data.get('tool_name')
                args = call_data.get('args', {})
                
                if not tool_name:
                    raise ValueError("Each tool call must have 'tool_name'")
                
                tool_calls.append(ToolCall(
                    tool_name=tool_name,
                    args=args
                ))
        
        reason = data.get('reason_brief', '')
        if len(reason) > 300:
            reason = reason[:300]
        
        stop_condition = data.get('stop_condition', '')
        
        return PlannerOutput(
            need_tools=need_tools,
            tool_calls=tool_calls,
            reason_brief=reason,
            stop_condition=stop_condition,
            raw_response=response
        )
    
    def _extract_json(self, response: str) -> str:
        """
        Extract JSON from LLM response
        
        Handles cases where LLM includes explanatory text
        
        Args:
            response: Raw response string
        
        Returns:
            JSON string
        """
        
        # Try to find JSON block
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            return json_match.group(0)
        
        # If no clear JSON found, try to parse the whole response
        return response.strip()
    
    def check_repeated_calls(self, current_calls: List[ToolCall]) -> bool:
        """
        Check if we're about to repeat the same tool calls
        
        This helps prevent infinite loops
        
        Args:
            current_calls: Tool calls we're about to make
        
        Returns:
            True if calls are different from previous attempt, False if repeated
        """
        
        if len(self.state.history) < 2:
            return True  # Not enough history to detect repetition
        
        # Get previous loop
        prev_loop = self.state.history[-1]
        if not prev_loop.planner_output or not prev_loop.planner_output.tool_calls:
            return True
        
        prev_calls = prev_loop.planner_output.tool_calls
        
        # Check if calls are the same
        if len(current_calls) != len(prev_calls):
            return True
        
        for current, previous in zip(current_calls, prev_calls):
            if (current.tool_name != previous.tool_name or
                current.args != previous.args):
                return True
        
        # Calls are identical - we're repeating
        return False
    
    def get_available_tools(self) -> List[str]:
        """
        Get list of available tool names
        
        Returns:
            List of tool names
        """
        
        specs = self.tool_specs.split('\n')
        tools = []
        
        for line in specs:
            # Match lines like "1. list_dir"
            match = re.match(r'\d+\.\s+(\w+)', line)
            if match:
                tools.append(match.group(1))
        
        return tools

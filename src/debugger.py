"""
Debugger - Debug output management
Controls debug logging across the agent system
"""

from typing import Dict, Any, Optional
import json


class Debugger:
    """
    Debug logging system for agent execution
    
    Levels:
    - 'none': No debug output
    - 'basic': Key steps and decisions
    - 'verbose': Detailed information about each step
    """
    
    def __init__(self, enabled: bool = False, level: str = 'basic'):
        """
        Initialize debugger
        
        Args:
            enabled: Whether debug output is enabled
            level: Debug level ('none', 'basic', 'verbose')
        """
        self.enabled = enabled
        self.level = level
        self.loop_count = 0
    
    def _format_output(self, section: str, message: str) -> str:
        """Format debug output"""
        return f"[DEBUG {section}] {message}"
    
    def print(self, section: str, message: str) -> None:
        """Print debug message if enabled"""
        if not self.enabled:
            return
        
        print(self._format_output(section, message))
    
    def print_dict(self, section: str, label: str, data: Dict[str, Any]) -> None:
        """Print dictionary as JSON"""
        if not self.enabled:
            return
        
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            print(self._format_output(section, f"{label}:\n{json_str}"))
        except Exception as e:
            print(self._format_output(section, f"{label}: (failed to serialize: {e})"))
    
    # === Agent Loop ===
    
    def loop_start(self, loop_num: int, user_request: str) -> None:
        """Log agent loop start"""
        self.loop_count = loop_num
        self.print("AGENT_LOOP", f"=== LOOP {loop_num} START ===")
        if self.level == 'verbose':
            self.print("AGENT_LOOP", f"User request: {user_request}")
    
    def loop_end(self, loop_num: int, reason: str) -> None:
        """Log agent loop end"""
        self.print("AGENT_LOOP", f"=== LOOP {loop_num} END ({reason}) ===")
    
    # === Planner ===
    
    def planner_input(self, request: str, facts: list, tasks: list) -> None:
        """Log planner input"""
        if not self.enabled:
            return
        
        self.print("PLANNER", "--- Input to Planner ---")
        self.print("PLANNER", f"Request: {request}")
        
        if self.level == 'verbose':
            if facts:
                self.print("PLANNER", f"Facts: {facts}")
            if tasks:
                self.print("PLANNER", f"Tasks: {tasks}")
    
    def planner_output(self, output: Dict[str, Any]) -> None:
        """Log planner output"""
        if not self.enabled:
            return
        
        self.print("PLANNER", "--- Planner Output ---")
        if self.level == 'basic':
            need_tools = output.get('need_tools', False)
            reason = output.get('reason_brief', '')
            self.print("PLANNER", f"Need tools: {need_tools}")
            self.print("PLANNER", f"Reason: {reason}")
            
            tool_calls = output.get('tool_calls', [])
            self.print("PLANNER", f"Tool calls: {len(tool_calls)}")
            for tc in tool_calls:
                self.print("PLANNER", f"  - {tc.get('tool_name', 'unknown')}({tc.get('args', {})})")
        else:
            self.print_dict("PLANNER", "Full output", output)
    
    # === Tool Runner ===
    
    def tool_start(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Log tool execution start"""
        if not self.enabled:
            return
        
        self.print("TOOL_RUNNER", f"Executing: {tool_name}")
        if self.level == 'verbose':
            self.print("TOOL_RUNNER", f"  Args: {args}")
    
    def tool_end(self, tool_name: str, success: bool, output_len: int = 0) -> None:
        """Log tool execution end"""
        if not self.enabled:
            return
        
        status = "✓" if success else "✗"
        self.print("TOOL_RUNNER", f"{status} {tool_name} completed ({output_len} chars)")
    
    def tool_result_detail(self, tool_name: str, result: Dict[str, Any]) -> None:
        """Log complete tool result (verbose mode only)"""
        if not self.enabled or self.level != 'verbose':
            return
        
        self.print("TOOL_RUNNER", f"--- {tool_name} Full Result ---")
        self.print_dict("TOOL_RUNNER", "Result", result)
    
    def tool_error(self, tool_name: str, error: str) -> None:
        """Log tool error"""
        if not self.enabled:
            return
        
        self.print("TOOL_RUNNER", f"✗ {tool_name} ERROR: {error}")
    
    # === Responder ===
    
    def responder_input(self, request: str, tool_results: int) -> None:
        """Log responder input"""
        if not self.enabled:
            return
        
        self.print("RESPONDER", "--- Input to Responder ---")
        self.print("RESPONDER", f"Original request: {request}")
        self.print("RESPONDER", f"Tool results: {tool_results}")
    
    def responder_output(self, response: str, is_final: bool) -> None:
        """Log responder output"""
        if not self.enabled:
            return
        
        self.print("RESPONDER", "--- Responder Output ---")
        self.print("RESPONDER", f"Is final answer: {is_final}")
        
        if self.level == 'basic':
            response_preview = response[:100] + "..." if len(response) > 100 else response
            self.print("RESPONDER", f"Response: {response_preview}")
        else:
            self.print("RESPONDER", f"Response: {response}")
    
    # === State ===
    
    def state_update(self, facts: list, tasks: list, loop_num: int) -> None:
        """Log state update"""
        if not self.enabled or self.level != 'verbose':
            return
        
        self.print("STATE", f"Loop {loop_num} state:")
        self.print("STATE", f"  Facts: {len(facts)}")
        self.print("STATE", f"  Tasks: {len(tasks)}")
    
    def state_full(self, state_dict: Dict[str, Any]) -> None:
        """Log full state"""
        if not self.enabled or self.level != 'verbose':
            return
        
        self.print_dict("STATE", "Full state", state_dict)
    
    # === Summary ===
    
    def execution_complete(self, loops: int, total_time: float) -> None:
        """Log execution completion"""
        if not self.enabled:
            return
        
        self.print("EXECUTION", f"✓ Completed in {loops} loop(s), {total_time:.2f}s")
    
    def execution_error(self, error: str) -> None:
        """Log execution error"""
        if not self.enabled:
            return
        
        self.print("EXECUTION", f"✗ Error: {error}")


class DebugConfig:
    """Debug configuration from config.json"""
    
    @staticmethod
    def from_dict(config: Dict[str, Any]) -> Debugger:
        """Create Debugger from config dictionary"""
        
        debug_config = config.get('debug', {})
        enabled = debug_config.get('enabled', False)
        level = debug_config.get('level', 'basic')
        
        debugger = Debugger(enabled=enabled, level=level)
        
        # Store component flags for later use
        debugger.show_planner = debug_config.get('show_planner', True)
        debugger.show_tool_runner = debug_config.get('show_tool_runner', True)
        debugger.show_responder = debug_config.get('show_responder', True)
        debugger.show_state = debug_config.get('show_state', True)
        
        return debugger

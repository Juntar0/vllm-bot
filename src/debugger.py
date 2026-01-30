"""
Debugger - Debug output management
Controls debug logging across the agent system
"""

from typing import Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime


class Debugger:
    """
    Debug logging system for agent execution
    
    Levels:
    - 'none': No debug output
    - 'basic': Key steps and decisions (console only)
    - 'verbose': Detailed information (console)
    - 'file': Full details logged to file (even if console is off)
    
    Note: File logging always captures full details regardless of console setting
    """
    
    def __init__(self, enabled: bool = False, level: str = 'basic', log_file: Optional[str] = None):
        """
        Initialize debugger
        
        Args:
            enabled: Whether debug output is enabled on console
            level: Debug level ('none', 'basic', 'verbose')
            log_file: Optional file path for complete logging (always full details)
        """
        self.enabled = enabled
        self.level = level
        self.loop_count = 0
        self.log_file = log_file
        
        # Create log file if specified
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            # Clear previous log
            with open(log_path, 'w') as f:
                f.write(f"=== vLLM Bot Debug Log ===\n")
                f.write(f"Started: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
    
    def _format_output(self, section: str, message: str) -> str:
        """Format debug output"""
        return f"[DEBUG {section}] {message}"
    
    def _log_to_file(self, section: str, message: str, full_detail: str = "") -> None:
        """Log message to file with full details"""
        if not self.log_file:
            return
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().isoformat()
                f.write(f"[{timestamp}] [{section}] {message}\n")
                if full_detail:
                    f.write(f"  FULL_DETAIL:\n")
                    # Write JSON directly without line-by-line splitting to preserve formatting
                    f.write(f"    {full_detail}\n")
                f.write("\n")
                f.flush()  # Force write to disk immediately
        except Exception as e:
            print(f"Warning: Failed to write to log file: {e}")
    
    def print(self, section: str, message: str) -> None:
        """Print debug message if enabled (console only)"""
        # Console output
        if self.enabled:
            print(self._format_output(section, message))
        
        # Always log to file
        self._log_to_file(section, message)
    
    def print_dict(self, section: str, label: str, data: Dict[str, Any]) -> None:
        """Print dictionary as JSON"""
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            message = f"{label}:"
            
            # Console output
            if self.enabled:
                print(self._format_output(section, f"{label}:\n{json_str}"))
            
            # Always log to file with full JSON
            self._log_to_file(section, message, json_str)
        except Exception as e:
            error_msg = f"{label}: (failed to serialize: {e})"
            if self.enabled:
                print(self._format_output(section, error_msg))
            self._log_to_file(section, error_msg)
    
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
        """Log complete tool result
        
        Console: Preview version (500 chars max for output field only)
        File: ALWAYS logged with COMPLETE details (no truncation)
        """
        # Console: show preview if verbose mode
        if self.enabled and self.level == 'verbose':
            self.print("TOOL_RUNNER", f"--- {tool_name} Full Result ---")
            console_result = dict(result)
            if 'output' in console_result and len(console_result['output']) > 500:
                console_result['output'] = console_result['output'][:500] + '...[TRUNCATED - see log file]'
            if self.enabled:
                print(self._format_output("TOOL_RUNNER", f"Result:\n{json.dumps(console_result, indent=2, ensure_ascii=False)}"))
        
        # File: ALWAYS log with complete output (never truncated)
        self._log_to_file("TOOL_RUNNER", f"--- {tool_name} Full Result ---", 
                         json.dumps(result, indent=2, ensure_ascii=False))
    
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
        log_file = debug_config.get('log_file', None)
        
        debugger = Debugger(enabled=enabled, level=level, log_file=log_file)
        
        # Store component flags for later use
        debugger.show_planner = debug_config.get('show_planner', True)
        debugger.show_tool_runner = debug_config.get('show_tool_runner', True)
        debugger.show_responder = debug_config.get('show_responder', True)
        debugger.show_state = debug_config.get('show_state', True)
        
        return debugger

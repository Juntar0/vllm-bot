"""
Tool Runner - Execute tools safely
Runs Planner's tool_calls with security constraints and logging
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from src.state import ToolCall, ToolResult
from src.tool_constraints import ToolConstraints
from src.audit_log import AuditLog


class ToolRunner:
    """
    Execute tools (Planner's tool_calls) safely
    
    Responsibilities:
    - Validate tool calls against constraints
    - Execute tools in workspace
    - Capture and structure results
    - Log execution
    """
    
    def __init__(
        self,
        workspace_dir: str,
        constraints: ToolConstraints,
        audit_log: Optional[AuditLog] = None,
        debugger = None
    ):
        """
        Initialize ToolRunner
        
        Args:
            workspace_dir: Workspace directory for execution
            constraints: ToolConstraints instance
            audit_log: Optional AuditLog instance
            debugger: Optional Debugger instance
        """
        
        self.workspace_dir = Path(workspace_dir).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.constraints = constraints
        self.audit_log = audit_log
        self.debugger = debugger
        
        # Available tools
        self.tools: Dict[str, Callable] = {
            'list_dir': self.tool_list_dir,
            'read_file': self.tool_read_file,
            'write_file': self.tool_write_file,
            'edit_file': self.tool_edit_file,
            'exec_cmd': self.tool_exec_cmd,
            'grep': self.tool_grep,
        }
    
    def execute_calls(
        self,
        calls: List[ToolCall],
        loop_id: int
    ) -> List[ToolResult]:
        """
        Execute a list of tool calls
        
        Args:
            calls: List of ToolCall objects
            loop_id: Which loop iteration this is
        
        Returns:
            List of ToolResult objects
        """
        
        results = []
        
        for call in calls:
            result = self.execute_single(call, loop_id)
            results.append(result)
        
        return results
    
    def execute_single(
        self,
        call: ToolCall,
        loop_id: int
    ) -> ToolResult:
        """
        Execute a single tool call
        
        Args:
            call: ToolCall object
            loop_id: Which loop iteration this is
        
        Returns:
            ToolResult object
        """
        
        tool_name = call.tool_name
        args = call.args
        
        # Check if tool exists
        if tool_name not in self.tools:
            error = f"Unknown tool: {tool_name}"
            if self.audit_log:
                self.audit_log.log_tool_call(
                    loop_id=loop_id,
                    tool_name=tool_name,
                    args=args,
                    error=error,
                    success=False
                )
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=error
            )
        
        # Execute
        start = time.time()
        try:
            result = self.tools[tool_name](args)
            duration = time.time() - start
            
            # Log success
            if self.audit_log:
                self.audit_log.log_tool_call(
                    loop_id=loop_id,
                    tool_name=tool_name,
                    args=args,
                    output=result.get('output', ''),
                    error=result.get('error', ''),
                    exit_code=result.get('exit_code', 0),
                    duration_sec=duration,
                    success=not result.get('error')
                )
            
            tool_result = ToolResult(
                tool_name=tool_name,
                success=not result.get('error'),
                output=result.get('output', ''),
                error=result.get('error', ''),
                exit_code=result.get('exit_code', 0),
                duration_sec=duration
            )
            
            # Debug output
            if self.debugger:
                self.debugger.tool_result_detail(tool_name, {
                    'success': tool_result.success,
                    'output': tool_result.output[:500] + '...' if len(tool_result.output) > 500 else tool_result.output,
                    'error': tool_result.error,
                    'exit_code': tool_result.exit_code,
                    'duration_sec': tool_result.duration_sec,
                    'output_length': len(tool_result.output)
                })
            
            return tool_result
        
        except Exception as e:
            duration = time.time() - start
            error = str(e)
            
            if self.audit_log:
                self.audit_log.log_tool_call(
                    loop_id=loop_id,
                    tool_name=tool_name,
                    args=args,
                    error=error,
                    duration_sec=duration,
                    success=False
                )
            
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=error,
                duration_sec=duration
            )
    
    # ========== Tool Implementations ==========
    
    def tool_list_dir(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List files in a directory"""
        
        path = args.get('path', '.')
        
        # Validate path
        is_valid, err_msg = self.constraints.validate_path_and_command('list_dir', path)
        if not is_valid:
            return {'error': err_msg}
        
        try:
            dir_path = (self.workspace_dir / path).resolve()
            
            if not dir_path.exists():
                return {'error': f'Directory not found: {path}'}
            
            if not dir_path.is_dir():
                return {'error': f'Not a directory: {path}'}
            
            items = []
            for item in sorted(dir_path.iterdir()):
                if item.is_dir():
                    items.append(f"{item.name}/")
                else:
                    items.append(item.name)
            
            output = '\n'.join(items)
            return {'output': output, 'exit_code': 0}
        
        except Exception as e:
            return {'error': str(e)}
    
    def tool_read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents"""
        
        path = args.get('path')
        offset = args.get('offset', 0)
        limit = args.get('limit')
        
        if not path:
            return {'error': 'path argument required'}
        
        # Validate path
        is_valid, err_msg = self.constraints.validate_path_and_command('read_file', path)
        if not is_valid:
            return {'error': err_msg}
        
        try:
            file_path = (self.workspace_dir / path).resolve()
            
            if not file_path.exists():
                return {'error': f'File not found: {path}'}
            
            if not file_path.is_file():
                return {'error': f'Not a file: {path}'}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Apply offset and limit
            if offset > 0:
                lines = lines[offset:]
            if limit:
                lines = lines[:limit]
            
            content = ''.join(lines)
            
            # Truncate if too long
            content = self.constraints.truncate_output(content, self.constraints.max_output_size)
            
            return {'output': content, 'exit_code': 0}
        
        except Exception as e:
            return {'error': str(e)}
    
    def tool_write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write or create a file"""
        
        path = args.get('path')
        content = args.get('content', '')
        
        if not path:
            return {'error': 'path argument required'}
        
        # Validate path
        is_valid, err_msg = self.constraints.validate_path_and_command('write_file', path)
        if not is_valid:
            return {'error': err_msg}
        
        try:
            file_path = (self.workspace_dir / path).resolve()
            
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            output = f"Wrote {len(content)} chars to {path}"
            return {'output': output, 'exit_code': 0}
        
        except Exception as e:
            return {'error': str(e)}
    
    def tool_edit_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Edit file by replacing text"""
        
        path = args.get('path')
        old_text = args.get('oldText')
        new_text = args.get('newText')
        
        if not path or old_text is None or new_text is None:
            return {'error': 'path, oldText, and newText arguments required'}
        
        # Validate path
        is_valid, err_msg = self.constraints.validate_path_and_command('edit_file', path)
        if not is_valid:
            return {'error': err_msg}
        
        try:
            file_path = (self.workspace_dir / path).resolve()
            
            if not file_path.exists():
                return {'error': f'File not found: {path}'}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if old_text exists
            if old_text not in content:
                return {'error': f'Text not found in {path}'}
            
            # Check if old_text appears more than once
            count = content.count(old_text)
            if count > 1:
                return {'error': f'Text appears {count} times in {path} (must be unique)'}
            
            # Replace
            new_content = content.replace(old_text, new_text, 1)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            output = f"Successfully edited {path}"
            return {'output': output, 'exit_code': 0}
        
        except Exception as e:
            return {'error': str(e)}
    
    def tool_exec_cmd(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute shell command"""
        
        command = args.get('command')
        timeout = args.get('timeout')
        
        if not command:
            return {'error': 'command argument required'}
        
        # Validate command
        if not self.constraints.validate_command(command):
            return {'error': f'Command not allowed: {command}'}
        
        # Get effective timeout
        timeout = self.constraints.get_effective_timeout(timeout)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Combine output
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            # Truncate
            output = self.constraints.truncate_output(output, self.constraints.max_output_size)
            
            return {
                'output': output,
                'exit_code': result.returncode
            }
        
        except subprocess.TimeoutExpired:
            return {
                'error': f'Command timed out after {timeout}s',
                'exit_code': 124  # Standard timeout exit code
            }
        except Exception as e:
            return {
                'error': str(e),
                'exit_code': 1
            }
    
    def tool_grep(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for text in files"""
        
        pattern = args.get('pattern')
        path = args.get('path', '.')
        
        if not pattern:
            return {'error': 'pattern argument required'}
        
        # Validate path
        is_valid, err_msg = self.constraints.validate_path_and_command('grep', path)
        if not is_valid:
            return {'error': err_msg}
        
        try:
            search_path = (self.workspace_dir / path).resolve()
            
            if not search_path.exists():
                return {'error': f'Path not found: {path}'}
            
            matches = []
            
            # Search in files
            if search_path.is_file():
                with open(search_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern in line:
                            matches.append(f"{search_path.name}:{line_num}: {line.rstrip()}")
            
            elif search_path.is_dir():
                # Recursively search in directory
                for file_path in search_path.rglob('*'):
                    if file_path.is_file():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                for line_num, line in enumerate(f, 1):
                                    if pattern in line:
                                        rel_path = file_path.relative_to(self.workspace_dir)
                                        matches.append(f"{rel_path}:{line_num}: {line.rstrip()}")
                        except:
                            pass  # Skip binary files, etc.
            
            output = '\n'.join(matches) if matches else '(no matches)'
            output = self.constraints.truncate_output(output, self.constraints.max_output_size)
            
            return {'output': output, 'exit_code': 0}
        
        except Exception as e:
            return {'error': str(e)}

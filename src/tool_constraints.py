"""
Tool Constraints - Security constraints enforcement
Enforces path restrictions, command allowlists, and resource limits
"""

from pathlib import Path
from typing import List, Optional, Set
import re


class ToolConstraints:
    """
    Security constraints for tool execution
    
    Enforces:
    - Path restrictions (only access allowed root)
    - Command allowlist (whitelist mode)
    - Resource limits (timeout, output size)
    - No path traversal
    """
    
    def __init__(
        self,
        allowed_root: str,
        command_allowlist: Optional[List[str]] = None,
        timeout_sec: int = 30,
        max_output_size: int = 200000,
        max_stderr_size: int = 50000
    ):
        """
        Initialize constraints
        
        Args:
            allowed_root: Root directory for file access (e.g., ./workspace)
            command_allowlist: List of allowed commands (if empty, all allowed)
            timeout_sec: Maximum execution time
            max_output_size: Maximum stdout size
            max_stderr_size: Maximum stderr size
        """
        
        self.allowed_root = Path(allowed_root).resolve()
        self.allowed_root.mkdir(parents=True, exist_ok=True)
        
        self.command_allowlist = set(command_allowlist or [])
        self.timeout_sec = timeout_sec
        self.max_output_size = max_output_size
        self.max_stderr_size = max_stderr_size
    
    def validate_path(self, path: str) -> bool:
        """
        Validate that a path is within allowed_root
        
        Args:
            path: Path to validate (can be relative or absolute)
        
        Returns:
            True if path is allowed, False otherwise
        """
        
        try:
            # Resolve the path relative to allowed_root
            full_path = (self.allowed_root / path).resolve()
            
            # Check if the path is within allowed_root
            # This prevents path traversal like ../../../etc/passwd
            full_path.relative_to(self.allowed_root)
            
            return True
        except (ValueError, RuntimeError):
            # relative_to raises ValueError if path is not relative to root
            return False
    
    def validate_command(self, command: str) -> bool:
        """
        Validate that a command is in the allowlist
        
        Args:
            command: Command to validate (e.g., 'ls', 'cat file.txt')
        
        Returns:
            True if command is allowed, False otherwise
        """
        
        # If allowlist is empty, allow all
        if not self.command_allowlist:
            return True
        
        # Extract the first word (command name)
        # Handle cases like: ls -la, grep "pattern" file
        parts = command.split()
        if not parts:
            return False
        
        cmd_name = parts[0]
        
        # Check if command is in allowlist
        return cmd_name in self.command_allowlist
    
    def validate_path_and_command(self, command: str, file_path: str = None) -> tuple[bool, str]:
        """
        Comprehensive validation for file-based tools
        
        Args:
            command: The tool being called (e.g., 'read_file', 'exec')
            file_path: Optional file path to validate
        
        Returns:
            (is_valid, error_message)
        """
        
        if file_path:
            if not self.validate_path(file_path):
                return False, f"Path outside allowed root: {file_path}"
            
            # Check for path traversal attempts
            if '../' in file_path or file_path.startswith('/'):
                return False, f"Path traversal detected: {file_path}"
        
        return True, ""
    
    def truncate_output(self, output: str, max_size: int) -> str:
        """
        Truncate output if it exceeds max size
        
        Args:
            output: Output string
            max_size: Maximum size in characters
        
        Returns:
            Truncated output
        """
        
        if len(output) <= max_size:
            return output
        
        # Keep beginning and end, show truncation message in middle
        kept_size = max_size // 2
        middle_msg = f"\n... (output truncated, {len(output) - max_size} chars hidden) ...\n"
        
        return output[:kept_size] + middle_msg + output[-kept_size:]
    
    def get_effective_timeout(self, requested_timeout: Optional[int] = None) -> int:
        """
        Get effective timeout (minimum of requested and constraint)
        
        Args:
            requested_timeout: User-requested timeout
        
        Returns:
            Effective timeout in seconds
        """
        
        if requested_timeout is None:
            return self.timeout_sec
        
        # Use minimum (most restrictive)
        return min(requested_timeout, self.timeout_sec)
    
    def summary(self) -> str:
        """Get a summary of constraints"""
        
        return f"""
Security Constraints:
- Allowed root: {self.allowed_root}
- Command allowlist: {list(self.command_allowlist) if self.command_allowlist else 'All allowed'}
- Timeout: {self.timeout_sec}s
- Max output: {self.max_output_size} chars
- Max stderr: {self.max_stderr_size} chars
        """

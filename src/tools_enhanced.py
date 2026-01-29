"""
Tools - Enhanced security implementation
Level 1: Dangerous pattern detection (simple, maintains flexibility)
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class ToolExecutor:
    def __init__(self, workspace_dir: str, config: Dict[str, Any]):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.config = config
        
        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Security settings
        self.exec_enabled = config.get("exec_enabled", True)
        self.exec_timeout = config.get("exec_timeout", 30)
        self.exec_max_output = config.get("exec_max_output", 200000)
        self.allowed_commands = set(config.get("allowed_commands", []))
    
    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return result
        """
        if tool_name == "read":
            return self._read(args)
        elif tool_name == "write":
            return self._write(args)
        elif tool_name == "edit":
            return self._edit(args)
        elif tool_name == "exec":
            return self._exec(args)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _validate_path(self, path: str) -> Path:
        """
        Validate that path is within workspace and resolve it
        """
        try:
            full_path = (self.workspace_dir / path).resolve()
            
            # Ensure path is within workspace
            if not str(full_path).startswith(str(self.workspace_dir)):
                raise ValueError(f"Path outside workspace: {path}")
            
            return full_path
        except Exception as e:
            raise ValueError(f"Invalid path: {path} - {e}")
    
    def _read(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read file contents
        """
        try:
            path = self._validate_path(args["path"])
            
            if not path.exists():
                return {"error": f"File not found: {args['path']}"}
            
            if not path.is_file():
                return {"error": f"Not a file: {args['path']}"}
            
            # Read with optional offset and limit
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            offset = args.get("offset", 0)
            limit = args.get("limit")
            
            if offset > 0:
                lines = lines[offset:]
            
            if limit:
                lines = lines[:limit]
            
            content = ''.join(lines)
            
            return {"result": content}
            
        except Exception as e:
            return {"error": str(e)}
    
    def _write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write or create a file
        """
        try:
            path = self._validate_path(args["path"])
            content = args["content"]
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {"result": f"Successfully wrote {len(content)} chars to {args['path']}"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def _edit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit a file by replacing exact text
        """
        try:
            path = self._validate_path(args["path"])
            
            if not path.exists():
                return {"error": f"File not found: {args['path']}"}
            
            old_text = args["oldText"]
            new_text = args["newText"]
            
            # Read current content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count occurrences
            count = content.count(old_text)
            
            if count == 0:
                return {"error": f"Text not found in {args['path']}"}
            
            if count > 1:
                return {"error": f"Text appears {count} times in {args['path']} (must be unique)"}
            
            # Replace
            new_content = content.replace(old_text, new_text, 1)
            
            # Write back
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {"result": f"Successfully edited {args['path']}"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def _exec(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute shell command (with ENHANCED security restrictions)
        
        Level 1: Dangerous pattern detection
        - Blocks command chaining (&&, ||, ;, |)
        - Blocks command substitution ($(), ``)
        - Blocks basic path traversal (../)
        - Simple but effective
        """
        if not self.exec_enabled:
            return {"error": "Command execution is disabled"}
        
        try:
            command = args["command"]
            
            # ========== ENHANCED: Dangerous pattern detection ==========
            dangerous_patterns = [
                ('&&', 'command chaining (&&)'),
                ('||', 'command chaining (||)'),
                (';', 'command chaining (;)'),
                ('|', 'piping (|)'),
                ('$(', 'command substitution $()'),
                ('`', 'command substitution ``'),
                ('../', 'path traversal (../)'),
                ('/..', 'path traversal (/..)')
            ]
            
            for pattern, description in dangerous_patterns:
                if pattern in command:
                    return {
                        "error": f"Dangerous pattern detected: {description}",
                        "suggestion": "Use separate tool calls instead of chaining commands"
                    }
            # ===========================================================
            
            # Simple allowlist check (first word)
            cmd_parts = command.split()
            if cmd_parts and self.allowed_commands:
                cmd_name = cmd_parts[0]
                if cmd_name not in self.allowed_commands:
                    return {"error": f"Command not allowed: {cmd_name}"}
            
            # Execute in workspace directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                timeout=self.exec_timeout
            )
            
            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            # Truncate if too long
            if len(output) > self.exec_max_output:
                middle = self.exec_max_output // 2
                output = (
                    output[:middle] +
                    f"\n\n... truncated {len(output) - self.exec_max_output} chars ...\n\n" +
                    output[-middle:]
                )
            
            return {
                "result": output,
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {self.exec_timeout}s"}
        except Exception as e:
            return {"error": str(e)}


# Tool definitions remain the same as original
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read file contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line offset to start reading from (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (optional)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write or create a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit",
            "description": "Edit a file by replacing exact text",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)"
                    },
                    "oldText": {
                        "type": "string",
                        "description": "Exact text to find and replace (must appear exactly once)"
                    },
                    "newText": {
                        "type": "string",
                        "description": "New text to replace with"
                    }
                },
                "required": ["path", "oldText", "newText"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "Execute a shell command in the workspace directory. Note: Command chaining (&&, ||, ;, |), command substitution ($(), ``), and path traversal (../) are blocked for security.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute. Use separate tool calls instead of chaining commands."
                    }
                },
                "required": ["command"]
            }
        }
    }
]

"""
Tools - File operations and command execution
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
        Validate and resolve path (prevent path traversal)
        """
        resolved = (self.workspace_dir / path).resolve()
        
        # Ensure path is within workspace
        try:
            resolved.relative_to(self.workspace_dir)
        except ValueError:
            raise ValueError(f"Path outside workspace: {path}")
        
        return resolved
    
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
            
            # Read with offset and limit support
            offset = args.get("offset", 0)
            limit = args.get("limit", 2000)
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                
                # Apply offset and limit
                selected = lines[offset:offset + limit]
                content = ''.join(selected)
                
                total_lines = len(lines)
                shown_lines = len(selected)
                
                result = f"Read {shown_lines} lines (total: {total_lines})\n"
                result += f"File: {args['path']}\n\n"
                result += content
                
                return {"result": result}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write file contents
        """
        try:
            path = self._validate_path(args["path"])
            content = args["content"]
            
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {"result": f"Successfully wrote to {args['path']}"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def _edit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit file by replacing exact text
        """
        try:
            path = self._validate_path(args["path"])
            old_text = args["oldText"]
            new_text = args["newText"]
            
            if not path.exists():
                return {"error": f"File not found: {args['path']}"}
            
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
        Execute shell command (with security restrictions)
        """
        if not self.exec_enabled:
            return {"error": "Command execution is disabled"}
        
        try:
            command = args["command"]
            
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


# Tool definitions for function calling (if vLLM model supports it)
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
                        "description": "File path (relative to workspace)"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting line (optional, default 0)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max lines to read (optional, default 2000)"
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
                        "description": "File path (relative to workspace)"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content to write"
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
                        "description": "File path (relative to workspace)"
                    },
                    "oldText": {
                        "type": "string",
                        "description": "Exact text to find (must match exactly)"
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
            "description": "Execute a shell command in the workspace directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    }
]

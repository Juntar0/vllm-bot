"""
Integrated Agent - Main entry point
Combines all modules: Memory, Planner, ToolRunner, Responder, and AgentLoop
"""

from typing import Dict, Any, Optional
from src.memory import Memory
from src.state import AgentState
from src.audit_log import AuditLog
from src.tool_constraints import ToolConstraints
from src.tool_runner import ToolRunner
from src.planner import Planner
from src.responder import Responder
from src.agent_loop import AgentLoop


class Agent:
    """
    Integrated Agent - Full system combining all components
    
    Components:
    - Memory: Long-term memory (preferences, environment, facts)
    - State: Short-term state (loop tracking, facts, tasks)
    - AuditLog: Execution logging
    - Planner: LLM-based tool selection
    - ToolRunner: Tool execution with security constraints
    - Responder: LLM-based response generation
    - AgentLoop: Orchestration loop (max 5 iterations)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize integrated agent
        
        Args:
            config: Configuration dictionary with:
              - vllm: vLLM API configuration
              - workspace: Workspace directory
              - security: Security settings
              - memory: Memory file path
              - audit: Audit logging
        """
        
        self.config = config
        
        # Initialize components
        self.memory = Memory(
            memory_file=config.get('memory', {}).get('path')
        )
        
        self.state = AgentState()
        
        self.audit_log = AuditLog(
            log_file=config.get('audit', {}).get('log_path')
        ) if config.get('audit', {}).get('enabled', True) else None
        
        # Tool constraints
        security_config = config.get('security', {})
        self.constraints = ToolConstraints(
            allowed_root=config.get('workspace', {}).get('dir', './workspace'),
            command_allowlist=security_config.get('allowed_commands', []),
            timeout_sec=security_config.get('timeout_sec', 30),
            max_output_size=security_config.get('max_output_size', 200000)
        )
        
        # Tool runner
        self.tool_runner = ToolRunner(
            workspace_dir=config.get('workspace', {}).get('dir', './workspace'),
            constraints=self.constraints,
            audit_log=self.audit_log
        )
        
        # Planner
        self.planner = Planner(
            config=config.get('vllm', {}),
            memory=self.memory,
            state=self.state,
            audit_log=self.audit_log
        )
        
        # Responder
        self.responder = Responder(
            config=config.get('vllm', {}),
            memory=self.memory,
            state=self.state,
            audit_log=self.audit_log
        )
        
        # Agent loop
        agent_config = config.get('agent', {})
        self.agent_loop = AgentLoop(
            planner=self.planner,
            tool_runner=self.tool_runner,
            responder=self.responder,
            state=self.state,
            memory=self.memory,
            audit_log=self.audit_log,
            max_loops=agent_config.get('max_loops', 5),
            loop_wait_sec=agent_config.get('loop_wait_sec', 0.5)
        )
    
    def run(self, user_request: str) -> str:
        """
        Run the agent on a user request
        
        Args:
            user_request: The user's request
        
        Returns:
            Final response from the agent
        """
        
        return self.agent_loop.run(user_request)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get execution summary
        
        Returns:
            Dictionary with execution stats
        """
        
        return self.agent_loop.get_execution_summary()
    
    def print_summary(self) -> None:
        """Print execution summary"""
        self.agent_loop.print_summary()
    
    def save_memory(self) -> None:
        """Save memory to file"""
        self.memory.save()
    
    def get_audit_log_summary(self) -> Optional[str]:
        """Get audit log summary"""
        if self.audit_log:
            return self.audit_log.export_summary()
        return None

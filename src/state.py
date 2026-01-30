"""
State - Short-term state management
Tracks the progress of a single conversation/task
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class ToolCall:
    """A tool call made by the Planner"""
    tool_name: str
    args: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolResult:
    """Result of a tool execution"""
    tool_name: str
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration_sec: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlannerOutput:
    """Output from the Planner LLM"""
    need_tools: bool
    tool_calls: List[ToolCall] = field(default_factory=list)
    reason_brief: str = ""
    stop_condition: str = ""
    raw_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'need_tools': self.need_tools,
            'tool_calls': [tc.to_dict() for tc in self.tool_calls],
            'reason_brief': self.reason_brief,
            'stop_condition': self.stop_condition,
        }


@dataclass
class ResponderOutput:
    """Output from the Responder LLM"""
    response: str  # Natural language response to user
    summary: str = ""  # Summary of executed operations
    next_action: str = ""  # What to do next if unresolved
    is_final_answer: bool = False  # Whether this is a final answer
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LoopRecord:
    """Record of one iteration of the Planner-ToolRunner-Responder loop"""
    loop_id: int
    timestamp: str
    planner_output: Optional[PlannerOutput] = None
    tool_results: List[ToolResult] = field(default_factory=list)
    responder_output: Optional[ResponderOutput] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'loop_id': self.loop_id,
            'timestamp': self.timestamp,
            'planner_output': self.planner_output.to_dict() if self.planner_output else None,
            'tool_results': [tr.to_dict() for tr in self.tool_results],
            'responder_output': self.responder_output.to_dict() if self.responder_output else None,
        }


class AgentState:
    """
    Short-term state for a single conversation
    
    Tracks:
    - Current loop count
    - History of all iterations
    - Facts gathered so far
    - Remaining tasks
    - Last tool results
    """
    
    def __init__(self):
        self.loop_count = 0
        self.max_loops = 5
        self.user_request = ""
        self.history: List[LoopRecord] = []
        self.facts: List[str] = []
        self.remaining_tasks: List[str] = []
        self.last_tool_results: List[ToolResult] = []
        self.created_at = datetime.now().isoformat()
    
    def reset(self, user_request: str = "") -> None:
        """Reset state for a new conversation"""
        self.loop_count = 0
        self.user_request = user_request
        self.history = []
        self.facts = []
        self.remaining_tasks = []
        self.last_tool_results = []
        self.created_at = datetime.now().isoformat()
    
    def add_user_request(self, user_request: str) -> None:
        """Add a new user request while preserving conversation history
        
        This is used for multi-turn conversations where each user message
        builds on previous context.
        """
        self.user_request = user_request
        self.loop_count = 0  # Reset loop counter for new request
        # Keep history, facts, and remaining_tasks from previous requests
    
    def start_loop(self, loop_id: int) -> None:
        """Mark the start of a new loop"""
        self.loop_count = loop_id
    
    def add_planner_output(self, output: PlannerOutput) -> None:
        """Record the Planner's decision"""
        if not self.history or self.history[-1].loop_id != self.loop_count:
            self.history.append(LoopRecord(
                loop_id=self.loop_count,
                timestamp=datetime.now().isoformat(),
                planner_output=output
            ))
        else:
            self.history[-1].planner_output = output
    
    def add_tool_results(self, results: List[ToolResult]) -> None:
        """Record tool execution results"""
        self.last_tool_results = results
        
        if not self.history or self.history[-1].loop_id != self.loop_count:
            self.history.append(LoopRecord(
                loop_id=self.loop_count,
                timestamp=datetime.now().isoformat(),
                tool_results=results
            ))
        else:
            self.history[-1].tool_results = results
    
    def add_responder_output(self, output: ResponderOutput) -> None:
        """Record the Responder's response"""
        if not self.history or self.history[-1].loop_id != self.loop_count:
            self.history.append(LoopRecord(
                loop_id=self.loop_count,
                timestamp=datetime.now().isoformat(),
                responder_output=output
            ))
        else:
            self.history[-1].responder_output = output
    
    def add_fact(self, fact: str) -> None:
        """Add a discovered fact"""
        if fact not in self.facts:
            self.facts.append(fact)
    
    def add_task(self, task: str) -> None:
        """Add a remaining task"""
        if task not in self.remaining_tasks:
            self.remaining_tasks.append(task)
    
    def complete_task(self, task: str) -> None:
        """Mark a task as completed"""
        if task in self.remaining_tasks:
            self.remaining_tasks.remove(task)
    
    def get_history_summary(self, max_loops: int = 3) -> str:
        """Get a summary of recent loop history for Planner context"""
        recent = self.history[-max_loops:] if len(self.history) > max_loops else self.history
        
        if not recent:
            return "## Loop History (none yet)"
        
        lines = [f"## Loop History (recent {len(recent)} loops)"]
        for record in recent:
            lines.append(f"\nLoop {record.loop_id}:")
            
            if record.planner_output:
                reason = record.planner_output.reason_brief
                tools_count = len(record.planner_output.tool_calls)
                lines.append(f"  Planner decision: {reason} (tools: {tools_count})")
            
            if record.tool_results:
                for result in record.tool_results:
                    status = "✓" if result.success else "✗"
                    output_preview = result.output[:80].replace('\n', ' ') if result.output else "(no output)"
                    if result.error:
                        lines.append(f"  {status} {result.tool_name}: ERROR: {result.error[:80]}")
                    else:
                        lines.append(f"  {status} {result.tool_name}: {output_preview}")
            
            if record.responder_output:
                response_preview = record.responder_output.response[:100].replace('\n', ' ')
                lines.append(f"  Response: {response_preview}")
        
        return '\n'.join(lines)
    
    def to_context(self) -> str:
        """Convert state to context for LLM prompts"""
        parts = [
            f"## Current State",
            f"Loop: {self.loop_count}/{self.max_loops}",
            f"Facts gathered: {len(self.facts)}",
            f"Tasks remaining: {len(self.remaining_tasks)}",
        ]
        
        if self.facts:
            parts.append("\n## Facts Gathered")
            for fact in self.facts[-5:]:  # Recent facts
                parts.append(f"- {fact}")
        
        if self.remaining_tasks:
            parts.append("\n## Remaining Tasks")
            for task in self.remaining_tasks:
                parts.append(f"- {task}")
        
        if self.last_tool_results:
            parts.append("\n## Last Tool Results")
            for result in self.last_tool_results[-3:]:  # Recent results
                status = "success" if result.success else "error"
                parts.append(f"- {result.tool_name}: {status} - {result.output[:80]}")
        
        return '\n'.join(parts)
    
    def should_stop(self) -> bool:
        """
        Determine if we should stop iterating
        
        Heuristics:
        - No remaining tasks
        - All facts gathered
        - Max loops reached
        """
        return (
            len(self.remaining_tasks) == 0 and
            len(self.facts) > 0
        ) or self.loop_count >= self.max_loops
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary"""
        return {
            'loop_count': self.loop_count,
            'max_loops': self.max_loops,
            'user_request': self.user_request,
            'history': [record.to_dict() for record in self.history],
            'facts': self.facts,
            'remaining_tasks': self.remaining_tasks,
            'created_at': self.created_at,
        }
    
    def to_json(self) -> str:
        """Serialize state to JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    def summary(self) -> str:
        """Get a summary of the state"""
        return f"""
State Summary:
- Loop {self.loop_count}/{self.max_loops}
- Facts: {len(self.facts)}
- Remaining tasks: {len(self.remaining_tasks)}
- Last tool results: {len(self.last_tool_results)} items
- Duration: from {self.created_at}
        """

"""
Agent Loop - Main orchestration loop
Coordinates Planner, Tool Runner, and Responder for complete task execution
"""

import time
from typing import Optional
from src.planner import Planner
from src.tool_runner import ToolRunner
from src.responder import Responder
from src.memory import Memory
from src.state import AgentState
from src.audit_log import AuditLog


class AgentLoop:
    """
    Main agent loop - orchestrates Planner -> ToolRunner -> Responder
    
    Flow:
    1. Planner decides what tools to call next (or if done)
    2. Tool Runner executes the tool calls
    3. Responder generates natural language response
    4. Check if we should continue or stop
    5. Repeat (max 5 loops)
    
    Key responsibilities:
    - Coordinate the three main components
    - Manage loop iterations
    - Check termination conditions
    - Log overall execution
    - Handle errors
    """
    
    def __init__(
        self,
        planner: Planner,
        tool_runner: ToolRunner,
        responder: Responder,
        state: AgentState,
        memory: Memory,
        audit_log: Optional[AuditLog] = None,
        max_loops: int = 5,
        loop_wait_sec: float = 0.5
    ):
        """
        Initialize AgentLoop
        
        Args:
            planner: Planner instance
            tool_runner: ToolRunner instance
            responder: Responder instance
            state: AgentState instance
            memory: Memory instance
            audit_log: Optional AuditLog instance
            max_loops: Maximum loop iterations
            loop_wait_sec: Wait between loops (for rate limiting)
        """
        
        self.planner = planner
        self.tool_runner = tool_runner
        self.responder = responder
        self.state = state
        self.memory = memory
        self.audit_log = audit_log
        self.max_loops = max_loops
        self.loop_wait_sec = loop_wait_sec
    
    def run(self, user_request: str) -> str:
        """
        Execute the agent loop
        
        Args:
            user_request: The user's original request
        
        Returns:
            Final response string
        """
        
        # Reset state for new conversation
        self.state.reset(user_request)
        
        # Start loop iterations
        for loop_id in range(1, self.max_loops + 1):
            try:
                self.state.start_loop(loop_id)
                
                # Step 1: Planner - Decide what to do
                plan = self._execute_planner_step(user_request)
                
                # Step 2: Tool Runner - Execute tools
                tool_results = self._execute_tool_step(plan, loop_id)
                
                # Step 3: Responder - Generate response
                responder_output = self._execute_responder_step(
                    user_request,
                    tool_results,
                    loop_id
                )
                
                # Step 4: Record loop result
                self.state.add_responder_output(responder_output)
                
                # Step 5: Check if we should stop
                if self._should_stop(plan, responder_output):
                    return responder_output.response
                
                # Wait before next loop (rate limiting)
                if loop_id < self.max_loops:
                    time.sleep(self.loop_wait_sec)
            
            except Exception as e:
                error_msg = f"Error in loop {loop_id}: {str(e)}"
                
                if self.audit_log:
                    self.audit_log.log_error(
                        loop_id=loop_id,
                        error_type='LoopError',
                        error_message=str(e),
                        context={'user_request': user_request}
                    )
                
                # Return error response
                return self._handle_error(error_msg, loop_id)
        
        # Reached max loops
        return self._final_response_on_limit()
    
    def _execute_planner_step(self, user_request: str) -> 'PlannerOutput':
        """
        Execute Planner step
        
        Args:
            user_request: User request
        
        Returns:
            PlannerOutput object
        """
        
        plan = self.planner.plan(user_request)
        
        # Record in state
        self.state.add_planner_output(plan)
        
        return plan
    
    def _execute_tool_step(self, plan: 'PlannerOutput', loop_id: int) -> list:
        """
        Execute Tool Runner step
        
        Args:
            plan: Planner's plan
            loop_id: Current loop ID
        
        Returns:
            List of ToolResult objects
        """
        
        tool_results = []
        
        if plan.need_tools and plan.tool_calls:
            # Execute the tools
            tool_results = self.tool_runner.execute_calls(
                plan.tool_calls,
                loop_id
            )
            
            # Record in state
            self.state.add_tool_results(tool_results)
        
        return tool_results
    
    def _execute_responder_step(
        self,
        user_request: str,
        tool_results: list,
        loop_id: int
    ) -> 'ResponderOutput':
        """
        Execute Responder step
        
        Args:
            user_request: User request
            tool_results: Results from tool execution
            loop_id: Current loop ID
        
        Returns:
            ResponderOutput object
        """
        
        responder_output = self.responder.respond(
            user_request,
            tool_results,
            loop_id
        )
        
        return responder_output
    
    def _should_stop(self, plan: 'PlannerOutput', responder_output: 'ResponderOutput') -> bool:
        """
        Determine if we should stop looping
        
        Heuristics:
        - No more tools needed
        - Task appears complete
        - All remaining tasks done
        - Final answer generated
        
        Args:
            plan: Planner's output
            responder_output: Responder's output
        
        Returns:
            True if we should stop, False to continue
        """
        
        # If Planner says no tools needed, we're likely done
        if not plan.need_tools:
            return True
        
        # If Responder says it's a final answer
        if responder_output.is_final_answer:
            return True
        
        # If no remaining tasks
        if len(self.state.remaining_tasks) == 0 and len(self.state.facts) > 0:
            return True
        
        return False
    
    def _final_response_on_limit(self) -> str:
        """
        Generate response when max loops reached
        
        Returns:
            Response string
        """
        
        response_parts = [
            f"Reached maximum loop limit ({self.max_loops} iterations).",
            "",
            "Summary of findings:"
        ]
        
        # Add discovered facts
        if self.state.facts:
            response_parts.append("\nFacts discovered:")
            for fact in self.state.facts:
                response_parts.append(f"  • {fact}")
        else:
            response_parts.append("  (No facts discovered)")
        
        # Add remaining tasks
        if self.state.remaining_tasks:
            response_parts.append("\nRemaining tasks:")
            for task in self.state.remaining_tasks:
                response_parts.append(f"  • {task}")
            response_parts.append("")
            response_parts.append("Please review the audit log for more details.")
        else:
            response_parts.append("\nAll tasks completed!")
        
        return "\n".join(response_parts)
    
    def _handle_error(self, error_msg: str, loop_id: int) -> str:
        """
        Handle errors during loop execution
        
        Args:
            error_msg: Error message
            loop_id: Loop that failed
        
        Returns:
            Error response string
        """
        
        return f"""Error occurred during execution (Loop {loop_id}):
{error_msg}

Please check the audit log for details.
Discovered facts so far: {len(self.state.facts)}
"""
    
    def get_execution_summary(self) -> dict:
        """
        Get summary of the execution
        
        Returns:
            Dictionary with execution stats
        """
        
        summary = {
            'total_loops': self.state.loop_count,
            'max_loops': self.max_loops,
            'facts_discovered': len(self.state.facts),
            'remaining_tasks': len(self.state.remaining_tasks),
            'completed': len(self.state.remaining_tasks) == 0,
            'tool_calls_total': 0,
            'tool_success_rate': 0.0,
        }
        
        # Calculate tool stats from history
        all_results = []
        for record in self.state.history:
            if record.tool_results:
                all_results.extend(record.tool_results)
        
        summary['tool_calls_total'] = len(all_results)
        
        if all_results:
            successful = sum(1 for r in all_results if r.success)
            summary['tool_success_rate'] = successful / len(all_results)
        
        return summary
    
    def print_summary(self) -> None:
        """Print execution summary"""
        
        summary = self.get_execution_summary()
        
        print("\n" + "=" * 80)
        print("EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Loops executed: {summary['total_loops']}/{summary['max_loops']}")
        print(f"Facts discovered: {summary['facts_discovered']}")
        print(f"Remaining tasks: {summary['remaining_tasks']}")
        print(f"Completed: {'Yes' if summary['completed'] else 'No'}")
        print(f"Tool calls: {summary['tool_calls_total']}")
        
        if summary['tool_calls_total'] > 0:
            success_pct = summary['tool_success_rate'] * 100
            print(f"Tool success rate: {success_pct:.1f}%")
        
        print("=" * 80)

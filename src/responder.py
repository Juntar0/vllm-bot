"""
Responder - Natural language response generation
Generates user-friendly responses based on tool results
"""

from typing import Optional, Dict, Any, List
from src.vllm_provider import VLLMProvider
from src.memory import Memory
from src.state import AgentState, ToolResult, ResponderOutput
from src.audit_log import AuditLog


class Responder(VLLMProvider):
    """
    Responder LLM - Generate natural language responses
    
    Responsibilities:
    - Explain what was executed
    - Summarize tool results
    - Present errors and next steps
    - Only state facts from tool results (no speculation)
    
    Input:
    - System instructions
    - MEMORY (user preferences, environment)
    - STATE (facts, remaining tasks)
    - User request
    - Tool results from current loop
    
    Output:
    - Natural language response to user
    - Summary of executed operations
    - Next action if unresolved
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        memory: Memory,
        state: AgentState,
        audit_log: Optional[AuditLog] = None
    ):
        """
        Initialize Responder
        
        Args:
            config: vLLM config dict with base_url, model, etc.
            memory: Memory instance
            state: AgentState instance
            audit_log: Optional AuditLog instance
        """
        super().__init__(config)
        
        self.memory = memory
        self.state = state
        self.audit_log = audit_log
    
    def respond(
        self,
        user_request: str,
        tool_results: List[ToolResult],
        loop_id: int
    ) -> ResponderOutput:
        """
        Generate a response based on tool results
        
        Args:
            user_request: The original user request
            tool_results: Results from tools executed in this loop
            loop_id: Which loop iteration this is
        
        Returns:
            ResponderOutput with natural language response
        """
        
        # Build system prompt
        system_prompt = self._build_system_prompt(user_request, tool_results, loop_id)
        
        # Create messages list
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": "Generate a natural language response based on the tool results above."
            }
        ]
        
        # Call LLM
        try:
            response = self.chat_completion(messages)
        except Exception as e:
            if self.audit_log:
                self.audit_log.log_error(
                    loop_id=loop_id,
                    error_type='ResponderLLMError',
                    error_message=str(e),
                    context={'user_request': user_request}
                )
            raise
        
        # Extract text from response
        if isinstance(response, dict):
            choices = response.get('choices', [])
            if choices and isinstance(choices[0], dict):
                response_text = choices[0].get('message', {}).get('content', '')
            else:
                response_text = str(response)
        else:
            response_text = str(response)
        
        # Parse output
        output = self._parse_responder_output(response_text, tool_results)
        
        # Log response
        if self.audit_log:
            self.audit_log.log_responder_response(
                loop_id=loop_id,
                response=output.response,
                tool_count=len(tool_results)
            )
        
        return output
    
    def _build_system_prompt(
        self,
        user_request: str,
        tool_results: List[ToolResult],
        loop_id: int
    ) -> str:
        """
        Build the system prompt for the Responder
        
        Includes:
        1. Instructions
        2. MEMORY context
        3. STATE summary
        4. Tool results
        5. User request
        """
        
        system_instruction = """You are a response agent for an OS automation system.

Your role is to explain the results of executed tools to the user in clear, natural language.
Keep responses SHORT and EASY TO READ.

RULES:
1. Only state facts from the tool results below
2. If tool execution failed, explain why briefly
3. Be VERY CONCISE - avoid unnecessary words
4. Use bullet points or numbered lists for clarity
5. Do NOT make assumptions beyond what tools returned
6. Do NOT speculate about system state
7. Respond in the same language as the user (日本語 if user writes in 日本語)

OUTPUT FORMAT (choose the most appropriate):
If showing file/directory listing:
  • List items with bullet points
  • One item per line
  • No extra explanation needed

If showing command output:
  • Show the output directly
  • Add brief explanation only if needed

If tool failed:
  • State what was attempted
  • State why it failed
  • Suggest 1-2 fix options

IMPORTANT: Keep it SHORT. One paragraph maximum unless complex.
"""
        
        memory_section = f"""User's Memory (preferences, environment, history):
{self.memory.to_context()}
"""
        
        state_section = f"""Current State:
{self.state.to_context()}

Facts gathered so far: {len(self.state.facts)}
Remaining tasks: {len(self.state.remaining_tasks)}
"""
        
        results_section = self._format_tool_results(tool_results)
        
        user_section = f"""Original User Request:
{user_request}

User's Goal: {self.state.remaining_tasks[0] if self.state.remaining_tasks else 'Complete the request'}
"""
        
        return f"""{system_instruction}

{memory_section}

{state_section}

{results_section}

{user_section}

Generate your response:
"""
    
    def _format_tool_results(self, tool_results: List[ToolResult]) -> str:
        """
        Format tool results for inclusion in prompt
        
        Args:
            tool_results: List of ToolResult objects
        
        Returns:
            Formatted string with tool results
        """
        
        if not tool_results:
            return "No tools were executed in this loop."
        
        lines = ["Tool Execution Results (Loop):"]
        
        for i, result in enumerate(tool_results, 1):
            lines.append(f"\n{i}. {result.tool_name}")
            
            if result.success:
                lines.append("   Status: ✓ Success")
                
                # Show first 200 chars of output
                output_preview = result.output[:200]
                if len(result.output) > 200:
                    output_preview += f"... ({len(result.output) - 200} more chars)"
                
                lines.append(f"   Output: {output_preview}")
            else:
                lines.append("   Status: ✗ Failed")
                lines.append(f"   Error: {result.error}")
            
            if result.duration_sec > 0:
                lines.append(f"   Duration: {result.duration_sec:.2f}s")
        
        return '\n'.join(lines)
    
    def _parse_responder_output(
        self,
        response_text: str,
        tool_results: List[ToolResult]
    ) -> ResponderOutput:
        """
        Parse and structure Responder output
        
        Args:
            response_text: Raw response from LLM
            tool_results: Tool results for context
        
        Returns:
            ResponderOutput object
        """
        
        # Determine if this is a final answer
        is_final = self._is_final_answer(tool_results, response_text)
        
        # Extract summary
        summary = self._extract_summary(response_text, tool_results)
        
        # Extract next action if needed
        next_action = self._extract_next_action(response_text) if not is_final else ""
        
        return ResponderOutput(
            response=response_text,
            summary=summary,
            next_action=next_action,
            is_final_answer=is_final
        )
    
    def _is_final_answer(
        self,
        tool_results: List[ToolResult],
        response_text: str
    ) -> bool:
        """
        Determine if this is a final answer or if more work is needed
        
        Heuristics:
        - All tools succeeded
        - No "remaining" or "next" in response
        - Task appears complete
        
        Args:
            tool_results: Tool execution results
            response_text: Responder's response text
        
        Returns:
            True if final answer, False if more work needed
        """
        
        # If there are remaining tasks and they weren't resolved
        if self.state.remaining_tasks:
            return False
        
        # If all tools failed
        if tool_results and all(not r.success for r in tool_results):
            return False
        
        # Check for "next step" or "still need" keywords
        keywords = ['next', 'remaining', 'still', 'need to', 'still need', 'more work']
        for keyword in keywords:
            if keyword in response_text.lower():
                # Might be unresolved, but not definitive
                pass
        
        return True
    
    def _extract_summary(
        self,
        response_text: str,
        tool_results: List[ToolResult]
    ) -> str:
        """
        Extract a brief summary from the response
        
        Args:
            response_text: Full response text
            tool_results: Tool results
        
        Returns:
            Brief summary
        """
        
        # Build from tool results
        summary_parts = []
        
        for result in tool_results:
            if result.success:
                summary_parts.append(f"✓ {result.tool_name} succeeded")
            else:
                summary_parts.append(f"✗ {result.tool_name} failed: {result.error[:50]}")
        
        if summary_parts:
            return "; ".join(summary_parts)
        
        # Fallback: use first 100 chars of response
        return response_text[:100]
    
    def _extract_next_action(self, response_text: str) -> str:
        """
        Extract the next action from the response
        
        Args:
            response_text: Full response text
        
        Returns:
            Next action suggestion
        """
        
        # Look for "next" sentences
        lines = response_text.split('\n')
        
        for i, line in enumerate(lines):
            lower_line = line.lower()
            if 'next' in lower_line or 'should' in lower_line or 'then' in lower_line:
                # Return this line and next as suggestion
                next_lines = [line]
                if i + 1 < len(lines):
                    next_lines.append(lines[i + 1])
                return '\n'.join(next_lines).strip()
        
        return ""
    
    def get_response_quality_score(
        self,
        response: ResponderOutput,
        tool_results: List[ToolResult]
    ) -> float:
        """
        Estimate response quality (0.0 to 1.0)
        
        Heuristics:
        - Response length (too short or too long is bad)
        - Tool success rate
        - Clarity (how much was explained)
        
        Args:
            response: ResponderOutput object
            tool_results: Tool results
        
        Returns:
            Quality score (0.0-1.0)
        """
        
        score = 0.5  # Base score
        
        # Tool success rate
        if tool_results:
            success_rate = sum(1 for r in tool_results if r.success) / len(tool_results)
            score += success_rate * 0.3
        
        # Response length (prefer 100-500 chars)
        resp_len = len(response.response)
        if 100 < resp_len < 500:
            score += 0.2
        elif resp_len > 50:
            score += 0.1
        
        # Final answer vs more work needed
        if response.is_final_answer:
            score += 0.3
        elif response.next_action:
            score += 0.15
        
        # Clamp to 0-1
        return min(max(score, 0.0), 1.0)

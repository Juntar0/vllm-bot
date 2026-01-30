"""
Audit Log - Comprehensive execution logging
Records all tool executions for debugging and audit trails
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class AuditLog:
    """
    Comprehensive audit logging for all tool executions
    
    Records for each tool call:
    - Timestamp
    - Loop ID
    - Tool name
    - Arguments
    - Result (output, error, exit code)
    - Duration
    - Success/failure status
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = Path(log_file) if log_file else Path('./data/runlog.jsonl')
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[Dict[str, Any]] = []
    
    def log_tool_call(
        self,
        loop_id: int,
        tool_name: str,
        args: Dict[str, Any],
        output: str = "",
        error: str = "",
        exit_code: int = 0,
        duration_sec: float = 0.0,
        success: bool = True
    ) -> None:
        """
        Log a tool call execution
        
        Args:
            loop_id: Which loop iteration this occurred in
            tool_name: Name of the tool (read_file, write_file, exec_cmd, etc.)
            args: Arguments passed to the tool
            output: Output from the tool
            error: Error message if failed
            exit_code: Process exit code
            duration_sec: How long it took
            success: Whether it succeeded
        """
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'loop_id': loop_id,
            'tool_name': tool_name,
            'args': args,
            'output': output[:500] if output else "",  # Truncate long outputs
            'error': error[:500] if error else "",
            'exit_code': exit_code,
            'duration_sec': duration_sec,
            'success': success,
        }
        
        self.entries.append(entry)
        self._append_to_file(entry)
    
    def _append_to_file(self, entry: Dict[str, Any]) -> None:
        """Append a single entry to the JSONL log file"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Warning: Failed to append to audit log: {e}")
    
    def log_planner_decision(
        self,
        loop_id: int,
        decision: Dict[str, Any],
        reasoning: str = ""
    ) -> None:
        """Log a Planner's decision"""
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'loop_id': loop_id,
            'event_type': 'planner_decision',
            'decision': decision,
            'reasoning': reasoning[:500] if reasoning else "",
        }
        
        self.entries.append(entry)
        self._append_to_file(entry)
    
    def log_responder_response(
        self,
        loop_id: int,
        response: str,
        tool_count: int
    ) -> None:
        """Log a Responder's response"""
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'loop_id': loop_id,
            'event_type': 'responder_response',
            'response_preview': response[:300],
            'tool_count_processed': tool_count,
        }
        
        self.entries.append(entry)
        self._append_to_file(entry)
    
    def log_error(
        self,
        loop_id: int,
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None
    ) -> None:
        """Log an error event"""
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'loop_id': loop_id,
            'event_type': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {},
        }
        
        self.entries.append(entry)
        self._append_to_file(entry)
    
    def get_entries(self, loop_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get log entries
        
        Args:
            loop_id: Filter by loop ID (optional)
        
        Returns:
            List of log entries
        """
        if loop_id is None:
            return self.entries
        
        return [e for e in self.entries if e.get('loop_id') == loop_id]
    
    def get_tool_summary(self) -> Dict[str, Any]:
        """Get a summary of all tool executions"""
        
        summary = {
            'total_calls': 0,
            'successful': 0,
            'failed': 0,
            'by_tool': {},
            'total_duration_sec': 0.0,
        }
        
        for entry in self.entries:
            if entry.get('event_type') != 'tool_call' and 'tool_name' in entry:
                tool_name = entry['tool_name']
                success = entry.get('success', False)
                duration = entry.get('duration_sec', 0.0)
                
                summary['total_calls'] += 1
                summary['total_duration_sec'] += duration
                
                if success:
                    summary['successful'] += 1
                else:
                    summary['failed'] += 1
                
                if tool_name not in summary['by_tool']:
                    summary['by_tool'][tool_name] = {
                        'calls': 0,
                        'successful': 0,
                        'failed': 0,
                        'total_duration_sec': 0.0,
                    }
                
                summary['by_tool'][tool_name]['calls'] += 1
                summary['by_tool'][tool_name]['total_duration_sec'] += duration
                
                if success:
                    summary['by_tool'][tool_name]['successful'] += 1
                else:
                    summary['by_tool'][tool_name]['failed'] += 1
        
        return summary
    
    def load_from_file(self) -> None:
        """Load all entries from JSONL log file"""
        if not self.log_file.exists():
            return
        
        self.entries = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        self.entries.append(entry)
        except Exception as e:
            print(f"Warning: Failed to load audit log: {e}")
    
    def export_summary(self) -> str:
        """Export a human-readable summary"""
        
        summary = self.get_tool_summary()
        lines = [
            "=== Audit Log Summary ===",
            f"Total tool calls: {summary['total_calls']}",
            f"Successful: {summary['successful']}",
            f"Failed: {summary['failed']}",
            f"Total duration: {summary['total_duration_sec']:.2f}s",
            "",
            "By Tool:",
        ]
        
        for tool_name, stats in summary['by_tool'].items():
            lines.append(
                f"  {tool_name}: {stats['calls']} calls "
                f"({stats['successful']}✓ {stats['failed']}✗) "
                f"{stats['total_duration_sec']:.2f}s"
            )
        
        return '\n'.join(lines)
    
    def clear(self) -> None:
        """Clear all log entries"""
        self.entries = []
        if self.log_file.exists():
            self.log_file.unlink()
    
    def export_as_json(self) -> str:
        """Export all entries as JSON"""
        return json.dumps(self.entries, indent=2, ensure_ascii=False)
    
    def get_last_n_entries(self, n: int) -> List[Dict[str, Any]]:
        """Get the last n entries"""
        return self.entries[-n:] if len(self.entries) > n else self.entries
    
    def analyze_loop(self, loop_id: int) -> Dict[str, Any]:
        """
        Analyze a specific loop's execution
        
        Returns:
        - Tools called
        - Success rate
        - Duration
        - Any errors
        """
        
        loop_entries = self.get_entries(loop_id)
        
        analysis = {
            'loop_id': loop_id,
            'entries_count': len(loop_entries),
            'tools_called': [],
            'total_duration_sec': 0.0,
            'all_successful': True,
            'errors': [],
        }
        
        for entry in loop_entries:
            if 'tool_name' in entry:
                tool_name = entry['tool_name']
                if tool_name not in analysis['tools_called']:
                    analysis['tools_called'].append(tool_name)
                
                duration = entry.get('duration_sec', 0.0)
                analysis['total_duration_sec'] += duration
                
                if not entry.get('success', True):
                    analysis['all_successful'] = False
                    analysis['errors'].append({
                        'tool': tool_name,
                        'error': entry.get('error', 'Unknown error'),
                    })
        
        return analysis

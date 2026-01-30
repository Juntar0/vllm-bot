#!/usr/bin/env python3
"""
Test Phase 1 modules: Memory, State, AuditLog
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory import Memory
from src.state import (
    AgentState, ToolCall, ToolResult, PlannerOutput, ResponderOutput
)
from src.audit_log import AuditLog


def test_memory():
    """Test Memory module"""
    print("=" * 80)
    print("Testing Memory Module")
    print("=" * 80)
    
    memory = Memory('./test/test_data/memory.json')
    
    # Test preferences
    memory.set_preference('language', 'en')
    memory.set_preference('output_granularity', 'detailed')
    assert memory.get_preference('language') == 'en'
    print("✅ Preferences working")
    
    # Test environment
    memory.set_environment('os', 'Linux')
    memory.set_environment('work_dir', '/home/user/workspace')
    assert memory.get_environment('os') == 'Linux'
    print("✅ Environment working")
    
    # Test decisions
    memory.record_decision('commands', 'list_files', 'ls -la')
    assert memory.get_decision('commands', 'list_files') == 'ls -la'
    print("✅ Decisions working")
    
    # Test facts
    memory.record_fact('file_structure', '/home/user/projects contains: src/, tests/')
    memory.record_fact('system_info', 'Python 3.10 installed')
    facts = memory.get_facts()
    assert len(facts['file_structure']) == 1
    assert len(facts['system_info']) == 1
    print("✅ Facts working")
    
    # Test context generation
    context = memory.to_context()
    assert 'User Preferences' in context
    assert 'language: en' in context
    print("✅ Context generation working")
    
    # Test persistence
    memory.save()
    memory2 = Memory('./test/test_data/memory.json')
    assert memory2.get_preference('language') == 'en'
    print("✅ Persistence working")
    
    print()


def test_state():
    """Test State module"""
    print("=" * 80)
    print("Testing State Module")
    print("=" * 80)
    
    state = AgentState()
    state.reset("List all files in the workspace")
    
    # Test loop tracking
    state.start_loop(1)
    assert state.loop_count == 1
    print("✅ Loop tracking working")
    
    # Test Planner output recording
    plan = PlannerOutput(
        need_tools=True,
        tool_calls=[
            ToolCall('list_dir', {'path': '.'})
        ],
        reason_brief='Need to list files first',
        stop_condition='When all files are listed'
    )
    state.add_planner_output(plan)
    assert len(state.history) == 1
    print("✅ Planner output recording working")
    
    # Test tool results
    results = [
        ToolResult(
            tool_name='list_dir',
            success=True,
            output='file1.txt, file2.txt',
            duration_sec=0.1
        )
    ]
    state.add_tool_results(results)
    assert state.last_tool_results[0].tool_name == 'list_dir'
    print("✅ Tool results recording working")
    
    # Test Responder output
    responder = ResponderOutput(
        response='The workspace contains file1.txt and file2.txt',
        summary='Listed directory contents',
        is_final_answer=True
    )
    state.add_responder_output(responder)
    assert state.history[-1].responder_output.is_final_answer
    print("✅ Responder output recording working")
    
    # Test facts and tasks
    state.add_fact('workspace contains 2 files')
    state.add_task('examine file1.txt')
    state.complete_task('examine file1.txt')
    assert len(state.facts) == 1
    assert len(state.remaining_tasks) == 0
    print("✅ Facts and tasks working")
    
    # Test context generation
    context = state.to_context()
    assert 'Loop: 1/5' in context
    assert 'Facts gathered: 1' in context
    print("✅ Context generation working")
    
    # Test serialization
    json_str = state.to_json()
    data = json.loads(json_str)
    assert data['loop_count'] == 1
    print("✅ Serialization working")
    
    # Test stop condition
    state.remaining_tasks = []
    assert state.should_stop() == True
    print("✅ Stop condition working")
    
    print()


def test_audit_log():
    """Test AuditLog module"""
    print("=" * 80)
    print("Testing AuditLog Module")
    print("=" * 80)
    
    audit = AuditLog('./test/test_data/runlog.jsonl')
    
    # Test logging tool calls
    audit.log_tool_call(
        loop_id=1,
        tool_name='read_file',
        args={'path': 'test.txt'},
        output='File content here',
        exit_code=0,
        duration_sec=0.05,
        success=True
    )
    assert len(audit.entries) == 1
    print("✅ Tool call logging working")
    
    # Test Planner decision logging
    audit.log_planner_decision(
        loop_id=1,
        decision={'tools': ['read_file'], 'args': [{'path': 'test.txt'}]},
        reasoning='Need to read the file first'
    )
    assert len(audit.entries) == 2
    print("✅ Planner decision logging working")
    
    # Test Responder response logging
    audit.log_responder_response(
        loop_id=1,
        response='The file contains: File content here',
        tool_count=1
    )
    assert len(audit.entries) == 3
    print("✅ Responder response logging working")
    
    # Test error logging
    audit.log_error(
        loop_id=1,
        error_type='FileNotFoundError',
        error_message='File not found: missing.txt',
        context={'attempted_path': 'missing.txt'}
    )
    assert len(audit.entries) == 4
    print("✅ Error logging working")
    
    # Test filtering by loop
    loop1_entries = audit.get_entries(loop_id=1)
    assert len(loop1_entries) == 4
    print("✅ Entry filtering working")
    
    # Test tool summary
    summary = audit.get_tool_summary()
    assert summary['total_calls'] == 1
    assert summary['successful'] == 1
    assert 'read_file' in summary['by_tool']
    print("✅ Tool summary working")
    
    # Test export
    json_export = audit.export_as_json()
    data = json.loads(json_export)
    assert len(data) == 4
    print("✅ JSON export working")
    
    # Test summary export
    summary_text = audit.export_summary()
    assert 'Total tool calls: 1' in summary_text
    assert 'read_file' in summary_text
    print("✅ Summary export working")
    
    # Test persistence
    audit.log_tool_call(
        loop_id=2,
        tool_name='write_file',
        args={'path': 'output.txt', 'content': 'test'},
        success=True,
        duration_sec=0.02
    )
    
    audit2 = AuditLog('./test/test_data/runlog.jsonl')
    audit2.load_from_file()
    assert len(audit2.entries) >= 5
    print("✅ Persistence working")
    
    # Test loop analysis
    analysis = audit.analyze_loop(1)
    assert analysis['loop_id'] == 1
    assert 'read_file' in analysis['tools_called']
    assert analysis['all_successful'] == True
    print("✅ Loop analysis working")
    
    print()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " Phase 1 Module Tests ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        test_memory()
        test_state()
        test_audit_log()
        
        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("Phase 1 is complete! Ready to implement Phase 2 (Planner).")
        print()
        
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

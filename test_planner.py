#!/usr/bin/env python3
"""
Test Planner module
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.planner import Planner
from src.memory import Memory
from src.state import AgentState, ToolCall, PlannerOutput
from src.audit_log import AuditLog


def get_test_config():
    """Get standard test config"""
    return {
        'base_url': 'http://localhost:8000/v1',
        'model': 'test-model',
        'temperature': 0.0
    }


def test_planner_initialization():
    """Test Planner initialization"""
    print("\nTest 1: Planner Initialization")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    planner = Planner(
        config=config,
        memory=memory,
        state=state
    )
    
    assert planner.memory == memory
    assert planner.state == state
    assert planner.enable_function_calling == True
    print("✅ Planner initialization working")


def test_tool_specs_generation():
    """Test that tool specifications are generated correctly"""
    print("\nTest 2: Tool Specs Generation")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    planner = Planner(config=config, memory=memory, state=state)
    
    # Check tool specs format
    specs = planner.tool_specs
    assert 'list_dir' in specs
    assert 'read_file' in specs
    assert 'write_file' in specs
    assert 'exec_cmd' in specs
    print(f"✅ Generated specs for tools: {', '.join(planner.get_available_tools())}")


def test_available_tools():
    """Test getting available tools"""
    print("\nTest 3: Get Available Tools")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    planner = Planner(config=config, memory=memory, state=state)
    
    tools = planner.get_available_tools()
    
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert 'list_dir' in tools
    assert 'read_file' in tools
    assert 'write_file' in tools
    assert 'exec_cmd' in tools
    
    print(f"✅ Available tools: {tools}")


def test_system_prompt_generation():
    """Test that system prompt is generated correctly"""
    print("\nTest 4: System Prompt Generation")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    memory.set_preference('language', 'en')
    
    state = AgentState()
    state.reset("List all Python files in workspace")
    state.add_fact("Workspace is located at /home/user/workspace")
    state.add_task("Find all .py files")
    
    config = get_test_config()
    planner = Planner(config=config, memory=memory, state=state)
    
    prompt = planner._build_system_prompt("List all Python files")
    
    # Check prompt contains required sections
    assert 'planning agent' in prompt.lower()
    assert 'Available Tools' in prompt
    assert 'Long-term Memory' in prompt
    assert 'Current State' in prompt
    assert 'List all Python files' in prompt
    
    print(f"✅ Generated prompt ({len(prompt)} chars)")
    print(f"   - Contains tool specs: ✓")
    print(f"   - Contains memory context: ✓")
    print(f"   - Contains state summary: ✓")


def test_json_extraction():
    """Test JSON extraction from LLM response"""
    print("\nTest 5: JSON Extraction")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    planner = Planner(config=config, memory=memory, state=state)
    
    # Test case 1: Clean JSON
    response1 = '{"need_tools": true, "tool_calls": [], "reason_brief": "test"}'
    extracted1 = planner._extract_json(response1)
    assert '"need_tools"' in extracted1
    print("✅ Clean JSON extraction working")
    
    # Test case 2: JSON with explanatory text
    response2 = '''
    I will help you with this task.
    
    {"need_tools": false, "tool_calls": [], "reason_brief": "already known"}
    
    Let me know if you need anything else.
    '''
    extracted2 = planner._extract_json(response2)
    assert '"need_tools"' in extracted2
    assert 'I will help' not in extracted2
    print("✅ JSON extraction with surrounding text working")


def test_planner_output_parsing():
    """Test parsing of Planner output"""
    print("\nTest 6: Planner Output Parsing")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    planner = Planner(config=config, memory=memory, state=state)
    
    # Test case 1: Valid output with tools
    response1 = json.dumps({
        "need_tools": True,
        "tool_calls": [
            {"tool_name": "list_dir", "args": {"path": "."}}
        ],
        "reason_brief": "Need to see what files are available",
        "stop_condition": "When file list is obtained"
    })
    
    output1 = planner._parse_planner_output(response1)
    assert output1.need_tools == True
    assert len(output1.tool_calls) == 1
    assert output1.tool_calls[0].tool_name == "list_dir"
    print("✅ Parsing valid output with tools")
    
    # Test case 2: Valid output without tools
    response2 = json.dumps({
        "need_tools": False,
        "tool_calls": [],
        "reason_brief": "Answer is in memory already",
        "stop_condition": "Question answered"
    })
    
    output2 = planner._parse_planner_output(response2)
    assert output2.need_tools == False
    assert len(output2.tool_calls) == 0
    print("✅ Parsing valid output without tools")
    
    # Test case 3: Invalid JSON
    try:
        planner._parse_planner_output("not valid json")
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✅ Correctly rejects invalid JSON")
    
    # Test case 4: Missing required field
    try:
        planner._parse_planner_output('{"tool_calls": []}')
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✅ Correctly rejects missing 'need_tools' field")


def test_repeated_calls_detection():
    """Test detection of repeated tool calls"""
    print("\nTest 7: Repeated Calls Detection")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    state.reset("Test task")
    
    config = get_test_config()
    planner = Planner(config=config, memory=memory, state=state)
    
    # Empty history - no repeats
    calls1 = [ToolCall('read_file', {'path': 'test.txt'})]
    assert planner.check_repeated_calls(calls1) == True
    print("✅ No false positives with empty history")
    
    # Add first loop to history
    plan1 = PlannerOutput(
        need_tools=True,
        tool_calls=calls1,
        reason_brief="Read test file"
    )
    state.start_loop(1)
    state.add_planner_output(plan1)
    
    # Add second loop with same calls
    state.start_loop(2)
    plan2 = PlannerOutput(
        need_tools=True,
        tool_calls=calls1,
        reason_brief="Read test file again"
    )
    state.add_planner_output(plan2)
    
    # Now same calls should be detected as repeated
    assert planner.check_repeated_calls(calls1) == False
    print("✅ Detects identical repeated calls")
    
    # Different calls
    calls2 = [ToolCall('read_file', {'path': 'other.txt'})]
    assert planner.check_repeated_calls(calls2) == True
    print("✅ Distinguishes different calls")


def test_planner_context_building():
    """Test that context is properly built with memory and state"""
    print("\nTest 8: Context Building")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    memory.set_preference('language', 'en')
    memory.set_environment('os', 'Linux')
    memory.record_decision('commands', 'list_cmd', 'ls -la')
    
    state = AgentState()
    state.reset("Find Python files")
    state.add_fact("Workspace contains src/ and tests/ directories")
    state.add_task("Search for .py files")
    
    config = get_test_config()
    planner = Planner(config=config, memory=memory, state=state)
    
    prompt = planner._build_system_prompt("Find Python files")
    
    # Verify memory is included
    assert 'en' in prompt or 'English' in prompt.lower()
    assert 'Linux' in prompt
    
    # Verify state is included
    assert '.py' in prompt
    assert 'src/' in prompt or 'tests/' in prompt
    
    print("✅ Memory integrated into prompt")
    print("✅ State integrated into prompt")


def test_long_reason_truncation():
    """Test that overly long reason_brief is truncated"""
    print("\nTest 9: Reason Truncation")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    planner = Planner(config=config, memory=memory, state=state)
    
    long_reason = "a" * 500  # 500 characters
    response = json.dumps({
        "need_tools": False,
        "tool_calls": [],
        "reason_brief": long_reason,
        "stop_condition": "done"
    })
    
    output = planner._parse_planner_output(response)
    
    assert len(output.reason_brief) <= 300
    print(f"✅ Long reason truncated from {len(long_reason)} to {len(output.reason_brief)} chars")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " Planner Module Tests ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        test_planner_initialization()
        test_tool_specs_generation()
        test_available_tools()
        test_system_prompt_generation()
        test_json_extraction()
        test_planner_output_parsing()
        test_repeated_calls_detection()
        test_planner_context_building()
        test_long_reason_truncation()
        
        print("\n" + "=" * 80)
        print("✅ ALL PLANNER TESTS PASSED (9/9)")
        print("=" * 80)
        print()
        print("Planner module is ready for integration!")
        print()
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

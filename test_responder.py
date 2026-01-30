#!/usr/bin/env python3
"""
Test Responder module
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.responder import Responder
from src.memory import Memory
from src.state import AgentState, ToolResult


def get_test_config():
    """Get standard test config"""
    return {
        'base_url': 'http://localhost:8000/v1',
        'model': 'test-model',
        'temperature': 0.0
    }


def test_responder_initialization():
    """Test Responder initialization"""
    print("\nTest 1: Responder Initialization")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    responder = Responder(
        config=config,
        memory=memory,
        state=state
    )
    
    assert responder.memory == memory
    assert responder.state == state
    print("✅ Responder initialization working")


def test_system_prompt_generation():
    """Test system prompt generation"""
    print("\nTest 2: System Prompt Generation")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    memory.set_preference('language', 'en')
    
    state = AgentState()
    state.reset("List all Python files")
    state.add_fact("Found 5 Python files")
    state.add_task("Count the files")
    
    config = get_test_config()
    responder = Responder(config=config, memory=memory, state=state)
    
    tool_results = [
        ToolResult(
            tool_name='list_dir',
            success=True,
            output='file1.py\nfile2.py\nfile3.py',
            duration_sec=0.1
        )
    ]
    
    prompt = responder._build_system_prompt(
        "List all Python files",
        tool_results,
        1
    )
    
    # Verify prompt contains required sections
    assert 'response agent' in prompt.lower()
    assert 'Tool Execution Results' in prompt or 'tool' in prompt.lower()
    assert 'Memory' in prompt or 'memory' in prompt.lower()
    assert 'Current State' in prompt or 'State' in prompt
    assert 'User Request' in prompt or 'request' in prompt.lower()
    
    print(f"✅ Generated prompt ({len(prompt)} chars)")
    print(f"   - Contains instructions: ✓")
    print(f"   - Contains memory context: ✓")
    print(f"   - Contains state summary: ✓")
    print(f"   - Contains tool results: ✓")


def test_format_tool_results():
    """Test tool results formatting"""
    print("\nTest 3: Format Tool Results")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    responder = Responder(config=config, memory=memory, state=state)
    
    # Test with successful tools
    results_success = [
        ToolResult(
            tool_name='read_file',
            success=True,
            output='File content here',
            duration_sec=0.05
        ),
        ToolResult(
            tool_name='write_file',
            success=True,
            output='Wrote 100 chars',
            duration_sec=0.02
        )
    ]
    
    formatted = responder._format_tool_results(results_success)
    assert '✓ Success' in formatted
    assert 'read_file' in formatted
    assert 'write_file' in formatted
    print("✅ Success results formatted correctly")
    
    # Test with failed tools
    results_failure = [
        ToolResult(
            tool_name='exec_cmd',
            success=False,
            error='Command not found',
            duration_sec=0.01
        )
    ]
    
    formatted = responder._format_tool_results(results_failure)
    assert '✗ Failed' in formatted
    assert 'Command not found' in formatted
    print("✅ Failed results formatted correctly")
    
    # Test with no results
    formatted = responder._format_tool_results([])
    assert 'No tools' in formatted
    print("✅ Empty results handled")


def test_is_final_answer():
    """Test final answer detection"""
    print("\nTest 4: Final Answer Detection")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    responder = Responder(config=config, memory=memory, state=state)
    
    # Case 1: All tasks done
    state.reset("Test task")
    state.remaining_tasks = []
    
    result_success = ToolResult(
        tool_name='read_file',
        success=True,
        output='Found it'
    )
    
    is_final = responder._is_final_answer([result_success], "Here's the answer")
    assert is_final == True
    print("✅ Detects final answer when tasks complete")
    
    # Case 2: Tasks remaining
    state.add_task("Still need to check")
    is_final = responder._is_final_answer([result_success], "Here's the answer")
    assert is_final == False
    print("✅ Detects incomplete when tasks remain")
    
    # Case 3: All tools failed
    state.remaining_tasks = []
    result_failed = ToolResult(
        tool_name='exec_cmd',
        success=False,
        error='Failed'
    )
    
    is_final = responder._is_final_answer([result_failed], "Could not complete")
    assert is_final == False
    print("✅ Detects incomplete when all tools fail")


def test_extract_summary():
    """Test summary extraction"""
    print("\nTest 5: Summary Extraction")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    responder = Responder(config=config, memory=memory, state=state)
    
    # Test with mixed results
    results = [
        ToolResult(
            tool_name='list_dir',
            success=True,
            output='...'
        ),
        ToolResult(
            tool_name='read_file',
            success=False,
            error='File not found'
        )
    ]
    
    summary = responder._extract_summary(
        "Here's the response",
        results
    )
    
    assert 'list_dir' in summary
    assert 'read_file' in summary
    assert '✓' in summary or '✗' in summary
    
    print(f"✅ Summary extracted: {summary}")


def test_extract_next_action():
    """Test next action extraction"""
    print("\nTest 6: Next Action Extraction")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    responder = Responder(config=config, memory=memory, state=state)
    
    # Response with next steps
    response = """The file was found.
Next, we need to check its contents.
Then we can process it further."""
    
    next_action = responder._extract_next_action(response)
    assert len(next_action) > 0
    assert 'Next' in next_action or 'next' in next_action.lower()
    print(f"✅ Next action extracted: {next_action[:50]}...")
    
    # Response without next steps
    response_no_next = "The task is complete."
    next_action_none = responder._extract_next_action(response_no_next)
    assert next_action_none == "" or len(next_action_none) == 0
    print("✅ Handles responses without next steps")


def test_responder_output_parsing():
    """Test responder output parsing"""
    print("\nTest 7: Responder Output Parsing")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    state.reset("Test task")
    state.remaining_tasks = []
    
    config = get_test_config()
    responder = Responder(config=config, memory=memory, state=state)
    
    # Test output parsing
    response_text = """The file listing shows:
    - file1.txt
    - file2.py
    - file3.md
    
All files have been successfully listed."""
    
    results = [
        ToolResult(
            tool_name='list_dir',
            success=True,
            output='file1.txt\nfile2.py\nfile3.md'
        )
    ]
    
    output = responder._parse_responder_output(response_text, results)
    
    assert output.response == response_text
    assert output.is_final_answer == True
    assert 'list_dir' in output.summary
    print("✅ Output parsing working")


def test_quality_score():
    """Test response quality scoring"""
    print("\nTest 8: Response Quality Scoring")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    config = get_test_config()
    
    responder = Responder(config=config, memory=memory, state=state)
    
    # High quality response
    from src.state import ResponderOutput
    
    high_quality = ResponderOutput(
        response="Found 5 Python files:\n1. script1.py\n2. script2.py\n3. script3.py\n4. script4.py\n5. script5.py",
        summary="✓ list_dir succeeded",
        is_final_answer=True
    )
    
    results_good = [
        ToolResult(
            tool_name='list_dir',
            success=True,
            output='5 files found'
        )
    ]
    
    score_high = responder.get_response_quality_score(high_quality, results_good)
    assert 0.0 <= score_high <= 1.0
    assert score_high > 0.5  # Should be above average
    print(f"✅ High quality response scored: {score_high:.2f}")
    
    # Low quality response
    low_quality = ResponderOutput(
        response="Error",  # Too short
        summary="",
        is_final_answer=False
    )
    
    results_bad = [
        ToolResult(
            tool_name='exec_cmd',
            success=False,
            error='Command failed'
        )
    ]
    
    score_low = responder.get_response_quality_score(low_quality, results_bad)
    assert 0.0 <= score_low <= 1.0
    # Low quality should be lower than high quality
    assert score_low < score_high
    print(f"✅ Low quality response scored: {score_low:.2f} (lower than high: {score_high:.2f})")


def test_context_building():
    """Test that context is properly built"""
    print("\nTest 9: Context Building")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    memory.set_preference('language', 'en')
    memory.set_environment('os', 'Linux')
    
    state = AgentState()
    state.reset("Find all .txt files")
    state.add_fact("Workspace contains 10 text files")
    state.add_task("Filter by date modified")
    
    config = get_test_config()
    responder = Responder(config=config, memory=memory, state=state)
    
    results = [
        ToolResult(
            tool_name='grep',
            success=True,
            output='.txt files found'
        )
    ]
    
    prompt = responder._build_system_prompt(
        "Find all .txt files",
        results,
        1
    )
    
    # Verify context is included
    assert 'en' in prompt or 'language' in prompt.lower()
    assert 'Linux' in prompt
    assert 'Workspace contains' in prompt
    assert 'Filter by date' in prompt
    
    print("✅ Memory integrated into prompt")
    print("✅ State integrated into prompt")
    print("✅ User request integrated")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " Responder Module Tests ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        test_responder_initialization()
        test_system_prompt_generation()
        test_format_tool_results()
        test_is_final_answer()
        test_extract_summary()
        test_extract_next_action()
        test_responder_output_parsing()
        test_quality_score()
        test_context_building()
        
        print("\n" + "=" * 80)
        print("✅ ALL RESPONDER TESTS PASSED (9/9)")
        print("=" * 80)
        print()
        print("Responder module is ready for integration!")
        print()
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

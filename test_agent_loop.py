#!/usr/bin/env python3
"""
Test Agent Loop module
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

sys.path.insert(0, str(Path(__file__).parent))

from src.agent_loop import AgentLoop
from src.memory import Memory
from src.state import AgentState, ToolCall, PlannerOutput, ToolResult, ResponderOutput


class MockPlanner:
    """Mock Planner for testing"""
    def plan(self, user_request):
        return PlannerOutput(
            need_tools=True,
            tool_calls=[ToolCall('list_dir', {'path': '.'})],
            reason_brief='Need to list files',
            stop_condition='When file list obtained'
        )


class MockToolRunner:
    """Mock Tool Runner for testing"""
    def __init__(self, fail_on_loop=None):
        self.fail_on_loop = fail_on_loop
    
    def execute_calls(self, calls, loop_id):
        if self.fail_on_loop == loop_id:
            return [ToolResult(
                tool_name='list_dir',
                success=False,
                error='Simulated failure'
            )]
        
        return [ToolResult(
            tool_name='list_dir',
            success=True,
            output='file1.txt\nfile2.py',
            duration_sec=0.1
        )]


class MockResponder:
    """Mock Responder for testing"""
    def __init__(self, final_on_loop=1):
        self.final_on_loop = final_on_loop
    
    def respond(self, user_request, tool_results, loop_id):
        is_final = loop_id >= self.final_on_loop
        
        return ResponderOutput(
            response=f"Loop {loop_id}: Found {len(tool_results)} tool results",
            summary=f"Executed {len(tool_results)} tools",
            next_action="" if is_final else "Continue searching",
            is_final_answer=is_final
        )


def test_agent_loop_initialization():
    """Test AgentLoop initialization"""
    print("\nTest 1: AgentLoop Initialization")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder()
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory,
        max_loops=5
    )
    
    assert loop.planner == planner
    assert loop.tool_runner == tool_runner
    assert loop.responder == responder
    assert loop.max_loops == 5
    print("✅ AgentLoop initialized correctly")


def test_agent_loop_single_iteration():
    """Test a single loop iteration"""
    print("\nTest 2: Single Loop Iteration")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder(final_on_loop=1)  # Final on first loop
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory
    )
    
    response = loop.run("Test request")
    
    assert response is not None
    assert len(response) > 0
    assert "Loop 1" in response
    print(f"✅ Single iteration completed: {response[:50]}...")


def test_agent_loop_multiple_iterations():
    """Test multiple loop iterations"""
    print("\nTest 3: Multiple Loop Iterations")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder(final_on_loop=3)  # Final on loop 3
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory,
        loop_wait_sec=0  # No wait for tests
    )
    
    response = loop.run("Test request")
    
    assert response is not None
    assert "Loop 3" in response
    assert state.loop_count == 3
    print(f"✅ Multiple iterations completed in {state.loop_count} loops")


def test_agent_loop_max_loops():
    """Test reaching max loop limit"""
    print("\nTest 4: Max Loop Limit")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder(final_on_loop=999)  # Never final
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory,
        max_loops=3,
        loop_wait_sec=0
    )
    
    response = loop.run("Test request")
    
    assert state.loop_count == 3
    assert "maximum loop limit" in response.lower() or "Reached maximum" in response
    print(f"✅ Stopped at max loops: {state.loop_count}/3")


def test_should_stop_conditions():
    """Test different stop conditions"""
    print("\nTest 5: Stop Conditions")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder()
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory
    )
    
    # Test 1: No tools needed
    plan_no_tools = PlannerOutput(
        need_tools=False,
        tool_calls=[],
        reason_brief='No tools needed'
    )
    responder_output = ResponderOutput(
        response='Answer from memory',
        is_final_answer=False
    )
    
    assert loop._should_stop(plan_no_tools, responder_output) == True
    print("✅ Stops when no tools needed")
    
    # Test 2: Final answer
    plan_with_tools = PlannerOutput(
        need_tools=True,
        tool_calls=[ToolCall('read_file', {'path': 'test.txt'})],
        reason_brief='Read test file'
    )
    responder_final = ResponderOutput(
        response='Task complete',
        is_final_answer=True
    )
    
    assert loop._should_stop(plan_with_tools, responder_final) == True
    print("✅ Stops on final answer")
    
    # Test 3: More work needed
    responder_more = ResponderOutput(
        response='Need to do more',
        is_final_answer=False
    )
    
    assert loop._should_stop(plan_with_tools, responder_more) == False
    print("✅ Continues when more work needed")


def test_execution_summary():
    """Test execution summary generation"""
    print("\nTest 6: Execution Summary")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    state.reset("Test task")
    
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder(final_on_loop=2)
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory,
        loop_wait_sec=0
    )
    
    loop.run("Test request")
    
    summary = loop.get_execution_summary()
    
    assert summary['total_loops'] == 2
    assert summary['max_loops'] == 5
    assert summary['tool_calls_total'] == 2
    assert summary['tool_success_rate'] == 1.0
    print(f"✅ Execution summary: {summary['total_loops']} loops, {summary['tool_calls_total']} tool calls")


def test_error_handling():
    """Test error handling during execution"""
    print("\nTest 7: Error Handling")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    
    planner = MockPlanner()
    tool_runner = MockToolRunner(fail_on_loop=2)  # Fail on second loop
    responder = MockResponder(final_on_loop=999)
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory,
        max_loops=3,
        loop_wait_sec=0
    )
    
    response = loop.run("Test request")
    
    assert response is not None
    assert len(response) > 0
    # Should complete despite tool failure
    assert state.loop_count > 0
    print(f"✅ Error handled gracefully at loop {state.loop_count}")


def test_state_tracking():
    """Test state tracking during execution"""
    print("\nTest 8: State Tracking")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder(final_on_loop=1)
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory
    )
    
    response = loop.run("Test request")
    
    # Check state was populated
    assert len(state.history) > 0
    assert state.loop_count > 0
    
    # Check first history record
    first_record = state.history[0]
    assert first_record.planner_output is not None
    assert first_record.tool_results is not None
    assert first_record.responder_output is not None
    
    print(f"✅ State tracked correctly: {len(state.history)} loop records")


def test_loop_with_remaining_tasks():
    """Test loop behavior with remaining tasks"""
    print("\nTest 9: Remaining Tasks Handling")
    print("-" * 60)
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    state.reset("Find and process files")
    state.add_task("Find Python files")
    state.add_task("Count lines in each")
    
    initial_task_count = len(state.remaining_tasks)
    
    planner = MockPlanner()
    tool_runner = MockToolRunner()
    responder = MockResponder(final_on_loop=1)
    
    loop = AgentLoop(
        planner=planner,
        tool_runner=tool_runner,
        responder=responder,
        state=state,
        memory=memory
    )
    
    response = loop.run("Find and process files")
    
    # Should have started with tasks
    assert initial_task_count > 0
    # After execution, state contains history
    assert len(state.history) > 0
    print(f"✅ Tasks tracked: initial {initial_task_count} tasks, {len(state.history)} loop records")


def test_responder_quality_score():
    """Test that responder quality score works"""
    print("\nTest 10: Response Quality Score")
    print("-" * 60)
    
    from src.responder import Responder
    
    memory = Memory('./test_data/memory.json')
    state = AgentState()
    state.reset("Test task")
    
    # Use real Responder for quality score test
    config = {
        'base_url': 'http://localhost:8000/v1',
        'model': 'test-model'
    }
    real_responder = Responder(config=config, memory=memory, state=state)
    
    # Test with successful tool results
    results = [
        ToolResult(
            tool_name='read_file',
            success=True,
            output='File content here'
        )
    ]
    
    responder_output = ResponderOutput(
        response="The file contains: File content here",
        summary="✓ read_file succeeded",
        is_final_answer=True
    )
    
    score = real_responder.get_response_quality_score(responder_output, results)
    assert 0.0 <= score <= 1.0
    assert score > 0.5  # Should be decent quality
    print(f"✅ Quality score calculated: {score:.2f}")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " Agent Loop Tests ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        test_agent_loop_initialization()
        test_agent_loop_single_iteration()
        test_agent_loop_multiple_iterations()
        test_agent_loop_max_loops()
        test_should_stop_conditions()
        test_execution_summary()
        test_error_handling()
        test_state_tracking()
        test_loop_with_remaining_tasks()
        test_responder_quality_score()
        
        print("\n" + "=" * 80)
        print("✅ ALL AGENT LOOP TESTS PASSED (10/10)")
        print("=" * 80)
        print()
        print("Agent Loop module is ready for integration!")
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

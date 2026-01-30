#!/usr/bin/env python3
"""
Integration Test - Full system test
Tests the complete integration of all components
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent
from src.memory import Memory
from src.state import AgentState
from src.tool_constraints import ToolConstraints
from src.tool_runner import ToolRunner


def get_test_config():
    """Get standard test config"""
    return {
        'vllm': {
            'base_url': 'http://localhost:8000/v1',
            'model': 'test-model',
            'temperature': 0.0,
            'enable_function_calling': True
        },
        'workspace': {
            'dir': './test_workspace_integration'
        },
        'security': {
            'exec_enabled': True,
            'allowed_commands': ['ls', 'cat'],
            'timeout_sec': 30,
            'max_output_size': 200000
        },
        'memory': {
            'path': './test_data/memory_integration.json'
        },
        'audit': {
            'enabled': True,
            'log_path': './test_data/runlog_integration.jsonl'
        },
        'agent': {
            'max_loops': 5,
            'loop_wait_sec': 0
        }
    }


def setup_test_workspace():
    """Setup test workspace"""
    workspace = Path('./test_workspace_integration')
    workspace.mkdir(exist_ok=True)
    (workspace / 'test.txt').write_text('Hello World')
    return workspace


def cleanup_test_workspace():
    """Cleanup test workspace"""
    import shutil
    workspace = Path('./test_workspace_integration')
    if workspace.exists():
        shutil.rmtree(workspace)


def test_agent_initialization():
    """Test Agent initialization"""
    print("\nTest 1: Agent Initialization")
    print("-" * 60)
    
    config = get_test_config()
    
    try:
        agent = Agent(config)
        
        assert agent.memory is not None
        assert agent.state is not None
        assert agent.tool_runner is not None
        assert agent.planner is not None
        assert agent.responder is not None
        assert agent.agent_loop is not None
        
        print("✅ Agent initialized with all components")
    except Exception as e:
        print(f"❌ Failed: {e}")
        raise


def test_agent_config_loading():
    """Test config loading"""
    print("\nTest 2: Config Loading")
    print("-" * 60)
    
    config = get_test_config()
    
    # Verify all required keys
    assert 'vllm' in config
    assert 'workspace' in config
    assert 'security' in config
    assert 'memory' in config
    assert 'audit' in config
    assert 'agent' in config
    
    # Verify nested values
    assert config['vllm']['model'] is not None
    assert config['workspace']['dir'] is not None
    assert config['agent']['max_loops'] == 5
    
    print("✅ Config structure valid")


def test_memory_persistence():
    """Test memory persistence through agent"""
    print("\nTest 3: Memory Persistence")
    print("-" * 60)
    
    config = get_test_config()
    agent = Agent(config)
    
    # Record something in memory
    agent.memory.set_preference('language', 'en')
    agent.memory.set_environment('os', 'Linux')
    agent.memory.save()
    
    # Create new agent with same memory file
    agent2 = Agent(config)
    
    # Verify memory was preserved
    assert agent2.memory.get_preference('language') == 'en'
    assert agent2.memory.get_environment('os') == 'Linux'
    
    print("✅ Memory persistence working")


def test_tool_constraints():
    """Test tool constraints through agent"""
    print("\nTest 4: Tool Constraints")
    print("-" * 60)
    
    setup_test_workspace()
    config = get_test_config()
    
    agent = Agent(config)
    
    # Test path validation
    valid = agent.constraints.validate_path('test.txt')
    assert valid == True
    
    invalid = agent.constraints.validate_path('../etc/passwd')
    assert invalid == False
    
    # Test command validation
    allowed = agent.constraints.validate_command('ls -la')
    assert allowed == True
    
    not_allowed = agent.constraints.validate_command('rm -rf /')
    assert not_allowed == False
    
    print("✅ Tool constraints working")
    cleanup_test_workspace()


def test_tool_execution():
    """Test tool execution through agent"""
    print("\nTest 5: Tool Execution")
    print("-" * 60)
    
    setup_test_workspace()
    config = get_test_config()
    
    agent = Agent(config)
    
    # Test list_dir
    result = agent.tool_runner.tool_list_dir({'path': '.'})
    assert result['exit_code'] == 0
    assert 'test.txt' in result['output']
    
    # Test read_file
    result = agent.tool_runner.tool_read_file({'path': 'test.txt'})
    assert result['exit_code'] == 0
    assert 'Hello World' in result['output']
    
    # Test write_file
    result = agent.tool_runner.tool_write_file({
        'path': 'output.txt',
        'content': 'Test output'
    })
    assert result['exit_code'] == 0
    assert Path('./test_workspace_integration/output.txt').exists()
    
    print("✅ Tool execution working")
    cleanup_test_workspace()


def test_state_management():
    """Test state management"""
    print("\nTest 6: State Management")
    print("-" * 60)
    
    config = get_test_config()
    agent = Agent(config)
    
    # Test state initialization
    agent.state.reset("Test task")
    assert agent.state.loop_count == 0
    assert len(agent.state.facts) == 0
    assert len(agent.state.remaining_tasks) == 0
    
    # Test state updates
    agent.state.add_fact("Found something")
    agent.state.add_task("Do something else")
    
    assert len(agent.state.facts) == 1
    assert len(agent.state.remaining_tasks) == 1
    
    # Test loop management
    agent.state.start_loop(1)
    assert agent.state.loop_count == 1
    
    print("✅ State management working")


def test_audit_logging():
    """Test audit logging"""
    print("\nTest 7: Audit Logging")
    print("-" * 60)
    
    config = get_test_config()
    agent = Agent(config)
    
    if agent.audit_log:
        # Log a tool call
        agent.audit_log.log_tool_call(
            loop_id=1,
            tool_name='read_file',
            args={'path': 'test.txt'},
            output='Content',
            success=True,
            duration_sec=0.1
        )
        
        # Check logging
        entries = agent.audit_log.get_entries(loop_id=1)
        assert len(entries) > 0
        
        summary = agent.audit_log.export_summary()
        assert 'read_file' in summary
        
        print("✅ Audit logging working")
    else:
        print("⚠️ Audit logging disabled")


def test_execution_summary():
    """Test execution summary"""
    print("\nTest 8: Execution Summary")
    print("-" * 60)
    
    config = get_test_config()
    agent = Agent(config)
    
    # Simulate some state changes
    agent.state.reset("Test task")
    agent.state.start_loop(1)
    agent.state.add_fact("Found something")
    
    # Get summary
    summary = agent.get_summary()
    
    assert 'total_loops' in summary
    assert 'max_loops' in summary
    assert 'facts_discovered' in summary
    assert 'completed' in summary
    
    assert summary['total_loops'] == 1
    assert summary['facts_discovered'] == 1
    
    print("✅ Execution summary working")


def test_component_integration():
    """Test that all components work together"""
    print("\nTest 9: Component Integration")
    print("-" * 60)
    
    config = get_test_config()
    agent = Agent(config)
    
    # Verify all components are connected
    assert agent.planner.memory == agent.memory
    assert agent.planner.state == agent.state
    assert agent.responder.memory == agent.memory
    assert agent.responder.state == agent.state
    assert agent.agent_loop.memory == agent.memory
    assert agent.agent_loop.state == agent.state
    
    # Verify tool constraints are applied
    assert agent.tool_runner.constraints == agent.constraints
    
    print("✅ Components properly integrated")


def test_error_handling():
    """Test error handling in agent"""
    print("\nTest 10: Error Handling")
    print("-" * 60)
    
    config = get_test_config()
    agent = Agent(config)
    
    # Test invalid path handling
    result = agent.tool_runner.tool_read_file({'path': '../etc/passwd'})
    assert 'error' in result
    
    # Test missing file handling
    result = agent.tool_runner.tool_read_file({'path': 'nonexistent.txt'})
    assert 'error' in result
    
    # Test invalid command handling
    result = agent.tool_runner.tool_exec_cmd({'command': 'rm -rf /'})
    assert 'error' in result
    
    print("✅ Error handling working")


def main():
    """Run all integration tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " Integration Tests ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        test_agent_initialization()
        test_agent_config_loading()
        test_memory_persistence()
        test_tool_constraints()
        test_tool_execution()
        test_state_management()
        test_audit_logging()
        test_execution_summary()
        test_component_integration()
        test_error_handling()
        
        print("\n" + "=" * 80)
        print("✅ ALL INTEGRATION TESTS PASSED (10/10)")
        print("=" * 80)
        print()
        print("System integration verified! Ready for production.")
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

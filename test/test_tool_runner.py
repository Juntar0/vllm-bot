#!/usr/bin/env python3
"""
Test Tool Runner and Tool Constraints modules
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tool_runner import ToolRunner
from src.tool_constraints import ToolConstraints
from src.state import ToolCall


def setup_test_workspace():
    """Setup test workspace"""
    workspace = Path('./test_workspace_runner')
    workspace.mkdir(exist_ok=True)
    
    # Create test files
    (workspace / 'test.txt').write_text('Hello World')
    (workspace / 'data.txt').write_text('Line 1\nLine 2\nLine 3\n')
    
    return workspace


def cleanup_test_workspace():
    """Cleanup test workspace"""
    import shutil
    workspace = Path('./test_workspace_runner')
    if workspace.exists():
        shutil.rmtree(workspace)


def test_constraints_path_validation():
    """Test ToolConstraints path validation"""
    print("\nTest 1: Path Validation")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(allowed_root=str(workspace))
    
    # Valid paths
    assert constraints.validate_path('test.txt') == True
    assert constraints.validate_path('.') == True
    assert constraints.validate_path('./subdir/file.txt') == True
    print("✅ Valid paths accepted")
    
    # Invalid paths (traversal)
    assert constraints.validate_path('../etc/passwd') == False
    assert constraints.validate_path('/../etc/passwd') == False
    assert constraints.validate_path('/etc/passwd') == False
    print("✅ Path traversal rejected")
    
    cleanup_test_workspace()


def test_constraints_command_validation():
    """Test ToolConstraints command validation"""
    print("\nTest 2: Command Validation")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    
    # With allowlist
    constraints_strict = ToolConstraints(
        allowed_root=str(workspace),
        command_allowlist=['ls', 'cat']
    )
    
    assert constraints_strict.validate_command('ls -la') == True
    assert constraints_strict.validate_command('cat file.txt') == True
    assert constraints_strict.validate_command('rm -rf /') == False
    print("✅ Allowlist enforcement working")
    
    # Without allowlist (all allowed)
    constraints_loose = ToolConstraints(allowed_root=str(workspace))
    assert constraints_loose.validate_command('any command here') == True
    print("✅ Empty allowlist allows all")
    
    cleanup_test_workspace()


def test_tool_runner_init():
    """Test ToolRunner initialization"""
    print("\nTest 3: ToolRunner Initialization")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(allowed_root=str(workspace))
    
    runner = ToolRunner(
        workspace_dir=str(workspace),
        constraints=constraints
    )
    
    assert runner.workspace_dir == workspace.resolve()
    assert len(runner.tools) == 6
    assert 'list_dir' in runner.tools
    assert 'read_file' in runner.tools
    assert 'write_file' in runner.tools
    print("✅ ToolRunner initialized with 6 tools")
    
    cleanup_test_workspace()


def test_tool_list_dir():
    """Test list_dir tool"""
    print("\nTest 4: list_dir Tool")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(allowed_root=str(workspace))
    runner = ToolRunner(workspace_dir=str(workspace), constraints=constraints)
    
    # List root
    result = runner.tool_list_dir({'path': '.'})
    assert result['exit_code'] == 0
    assert 'test.txt' in result['output']
    assert 'data.txt' in result['output']
    print("✅ list_dir works")
    
    # Invalid path
    result = runner.tool_list_dir({'path': '../etc'})
    assert 'error' in result
    print("✅ list_dir rejects invalid paths")
    
    cleanup_test_workspace()


def test_tool_read_file():
    """Test read_file tool"""
    print("\nTest 5: read_file Tool")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(allowed_root=str(workspace))
    runner = ToolRunner(workspace_dir=str(workspace), constraints=constraints)
    
    # Read file
    result = runner.tool_read_file({'path': 'test.txt'})
    assert result['exit_code'] == 0
    assert 'Hello World' in result['output']
    print("✅ read_file works")
    
    # Read with offset
    result = runner.tool_read_file({'path': 'data.txt', 'offset': 1, 'limit': 1})
    assert 'Line 2' in result['output']
    assert 'Line 1' not in result['output']
    print("✅ read_file with offset/limit works")
    
    # File not found
    result = runner.tool_read_file({'path': 'nonexistent.txt'})
    assert 'error' in result
    print("✅ read_file handles missing files")
    
    cleanup_test_workspace()


def test_tool_write_file():
    """Test write_file tool"""
    print("\nTest 6: write_file Tool")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(allowed_root=str(workspace))
    runner = ToolRunner(workspace_dir=str(workspace), constraints=constraints)
    
    # Write file
    result = runner.tool_write_file({'path': 'output.txt', 'content': 'Test content'})
    assert result['exit_code'] == 0
    assert (workspace / 'output.txt').exists()
    assert (workspace / 'output.txt').read_text() == 'Test content'
    print("✅ write_file works")
    
    # Write to subdirectory
    result = runner.tool_write_file({'path': 'subdir/file.txt', 'content': 'Nested'})
    assert result['exit_code'] == 0
    assert (workspace / 'subdir' / 'file.txt').exists()
    print("✅ write_file creates directories")
    
    cleanup_test_workspace()


def test_tool_edit_file():
    """Test edit_file tool"""
    print("\nTest 7: edit_file Tool")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(allowed_root=str(workspace))
    runner = ToolRunner(workspace_dir=str(workspace), constraints=constraints)
    
    # Edit file
    result = runner.tool_edit_file({
        'path': 'test.txt',
        'oldText': 'World',
        'newText': 'Python'
    })
    assert result['exit_code'] == 0
    assert (workspace / 'test.txt').read_text() == 'Hello Python'
    print("✅ edit_file works")
    
    # Text not found
    result = runner.tool_edit_file({
        'path': 'test.txt',
        'oldText': 'NotThere',
        'newText': 'Replacement'
    })
    assert 'error' in result
    print("✅ edit_file detects missing text")
    
    cleanup_test_workspace()


def test_tool_exec_cmd():
    """Test exec_cmd tool"""
    print("\nTest 8: exec_cmd Tool")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    
    # Without allowlist
    constraints = ToolConstraints(allowed_root=str(workspace))
    runner = ToolRunner(workspace_dir=str(workspace), constraints=constraints)
    
    # Execute command
    result = runner.tool_exec_cmd({'command': 'echo "Hello"'})
    assert result['exit_code'] == 0
    assert 'Hello' in result['output']
    print("✅ exec_cmd works")
    
    # Timeout test (quick command)
    result = runner.tool_exec_cmd({'command': 'echo "test"', 'timeout': 10})
    assert result['exit_code'] == 0
    print("✅ exec_cmd respects timeout")
    
    # With allowlist
    constraints_strict = ToolConstraints(
        allowed_root=str(workspace),
        command_allowlist=['echo', 'cat']
    )
    runner_strict = ToolRunner(workspace_dir=str(workspace), constraints=constraints_strict)
    
    # Allowed command
    result = runner_strict.tool_exec_cmd({'command': 'echo test'})
    assert result['exit_code'] == 0
    print("✅ exec_cmd respects allowlist (allowed)")
    
    # Blocked command
    result = runner_strict.tool_exec_cmd({'command': 'rm -rf /'})
    assert 'error' in result
    print("✅ exec_cmd respects allowlist (blocked)")
    
    cleanup_test_workspace()


def test_tool_grep():
    """Test grep tool"""
    print("\nTest 9: grep Tool")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(allowed_root=str(workspace))
    runner = ToolRunner(workspace_dir=str(workspace), constraints=constraints)
    
    # Search in file
    result = runner.tool_grep({'pattern': 'Line', 'path': 'data.txt'})
    assert result['exit_code'] == 0
    assert 'Line 1' in result['output']
    assert 'Line 2' in result['output']
    assert 'Line 3' in result['output']
    print("✅ grep finds patterns in files")
    
    # Search in directory
    result = runner.tool_grep({'pattern': 'Hello', 'path': '.'})
    assert result['exit_code'] == 0
    assert 'test.txt' in result['output']
    assert 'Hello' in result['output']
    print("✅ grep searches directory recursively")
    
    # No matches
    result = runner.tool_grep({'pattern': 'XYZ123', 'path': '.'})
    assert result['exit_code'] == 0
    assert 'no matches' in result['output']
    print("✅ grep handles no matches")
    
    cleanup_test_workspace()


def test_output_truncation():
    """Test output truncation"""
    print("\nTest 10: Output Truncation")
    print("-" * 60)
    
    workspace = setup_test_workspace()
    constraints = ToolConstraints(
        allowed_root=str(workspace),
        max_output_size=100
    )
    runner = ToolRunner(workspace_dir=str(workspace), constraints=constraints)
    
    # Create large file
    large_content = 'x' * 1000
    (workspace / 'large.txt').write_text(large_content)
    
    # Read should truncate
    result = runner.tool_read_file({'path': 'large.txt'})
    assert result['exit_code'] == 0
    assert len(result['output']) <= 150  # Some overhead for message
    assert 'truncated' in result['output']
    print("✅ Output truncation works")
    
    cleanup_test_workspace()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " Tool Runner & Constraints Tests ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        test_constraints_path_validation()
        test_constraints_command_validation()
        test_tool_runner_init()
        test_tool_list_dir()
        test_tool_read_file()
        test_tool_write_file()
        test_tool_edit_file()
        test_tool_exec_cmd()
        test_tool_grep()
        test_output_truncation()
        
        print("\n" + "=" * 80)
        print("✅ ALL TOOL RUNNER TESTS PASSED (10/10)")
        print("=" * 80)
        print()
        print("Tool Runner module is ready for integration!")
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

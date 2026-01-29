#!/usr/bin/env python3
"""
exec セキュリティテスト
現在のシンプルな実装の脆弱性を検証
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.tools import ToolExecutor

def run_security_tests():
    """Run security vulnerability tests"""
    
    # Setup
    workspace_dir = Path('./workspace')
    workspace_dir.mkdir(exist_ok=True)
    
    # Create test file in workspace
    test_file = workspace_dir / 'test.txt'
    test_file.write_text('Hello from workspace')
    
    # Create test file outside workspace (for path traversal test)
    outside_file = Path('./test_outside.txt')
    outside_file.write_text('Outside workspace')
    
    config = {
        'exec_enabled': True,
        'allowed_commands': ['ls', 'cat', 'echo', 'grep', 'python', 'find'],
        'exec_timeout': 5,
        'exec_max_output': 200000
    }
    
    executor = ToolExecutor(
        workspace_dir=str(workspace_dir),
        config=config
    )
    
    # Test cases
    test_cases = [
        # 1. Command Chaining
        {
            'category': 'Command Chaining',
            'name': 'Chaining with &&',
            'command': 'ls && echo VULNERABLE',
            'threat_level': 'CRITICAL',
            'expected_behavior': 'Should block command chaining'
        },
        {
            'category': 'Command Chaining',
            'name': 'Chaining with ;',
            'command': 'ls ; echo VULNERABLE',
            'threat_level': 'CRITICAL',
            'expected_behavior': 'Should block command chaining'
        },
        {
            'category': 'Command Chaining',
            'name': 'Chaining with |',
            'command': 'echo test | cat',
            'threat_level': 'CRITICAL',
            'expected_behavior': 'Should block piping'
        },
        
        # 2. Command Substitution
        {
            'category': 'Command Substitution',
            'name': 'Subshell $()',
            'command': 'cat $(echo test.txt)',
            'threat_level': 'CRITICAL',
            'expected_behavior': 'Should block command substitution'
        },
        {
            'category': 'Command Substitution',
            'name': 'Backticks',
            'command': 'cat `echo test.txt`',
            'threat_level': 'CRITICAL',
            'expected_behavior': 'Should block command substitution'
        },
        
        # 3. Argument Injection
        {
            'category': 'Argument Injection',
            'name': 'Read /etc/passwd',
            'command': 'cat /etc/passwd',
            'threat_level': 'MEDIUM',
            'expected_behavior': 'Ideally block, but depends on policy'
        },
        {
            'category': 'Argument Injection',
            'name': 'List root directory',
            'command': 'ls /',
            'threat_level': 'MEDIUM',
            'expected_behavior': 'Ideally block, but depends on policy'
        },
        
        # 4. Interpreter Bypass
        {
            'category': 'Interpreter Bypass',
            'name': 'Python code execution',
            'command': 'python -c "print(\'VULNERABLE\')"',
            'threat_level': 'CRITICAL',
            'expected_behavior': 'Should block -c option'
        },
        {
            'category': 'Interpreter Bypass',
            'name': 'Python import os',
            'command': 'python -c "import os; print(os.getcwd())"',
            'threat_level': 'CRITICAL',
            'expected_behavior': 'Should block -c option'
        },
        
        # 5. Path Traversal
        {
            'category': 'Path Traversal',
            'name': 'Read parent directory',
            'command': 'cat ../test_outside.txt',
            'threat_level': 'MEDIUM',
            'expected_behavior': 'Should block path traversal'
        },
        {
            'category': 'Path Traversal',
            'name': 'List parent',
            'command': 'ls ../',
            'threat_level': 'MEDIUM',
            'expected_behavior': 'Should block path traversal'
        },
        
        # 6. Valid commands (should pass)
        {
            'category': 'Valid Commands',
            'name': 'List workspace',
            'command': 'ls',
            'threat_level': 'SAFE',
            'expected_behavior': 'Should allow'
        },
        {
            'category': 'Valid Commands',
            'name': 'Cat file in workspace',
            'command': 'cat test.txt',
            'threat_level': 'SAFE',
            'expected_behavior': 'Should allow'
        },
        {
            'category': 'Valid Commands',
            'name': 'Echo string',
            'command': 'echo "Hello World"',
            'threat_level': 'SAFE',
            'expected_behavior': 'Should allow'
        },
    ]
    
    # Run tests
    print("=" * 80)
    print("EXEC SECURITY TEST RESULTS")
    print("=" * 80)
    print()
    
    results = {
        'CRITICAL': {'blocked': 0, 'executed': 0},
        'MEDIUM': {'blocked': 0, 'executed': 0},
        'SAFE': {'blocked': 0, 'executed': 0}
    }
    
    current_category = None
    
    for i, test in enumerate(test_cases, 1):
        # Print category header
        if test['category'] != current_category:
            current_category = test['category']
            print()
            print(f"{'─' * 80}")
            print(f"  {current_category}")
            print(f"{'─' * 80}")
        
        print(f"\nTest {i}: {test['name']}")
        print(f"  Command: {test['command']}")
        print(f"  Threat Level: {test['threat_level']}")
        print(f"  Expected: {test['expected_behavior']}")
        
        result = executor._exec({'command': test['command']})
        
        if 'error' in result:
            print(f"  ✅ BLOCKED: {result['error']}")
            results[test['threat_level']]['blocked'] += 1
        else:
            output = result.get('result', '')[:150]
            exit_code = result.get('exit_code', 0)
            print(f"  ❌ EXECUTED (exit {exit_code}): {output}")
            results[test['threat_level']]['executed'] += 1
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    critical_blocked = results['CRITICAL']['blocked']
    critical_executed = results['CRITICAL']['executed']
    critical_total = critical_blocked + critical_executed
    
    medium_blocked = results['MEDIUM']['blocked']
    medium_executed = results['MEDIUM']['executed']
    medium_total = medium_blocked + medium_executed
    
    safe_blocked = results['SAFE']['blocked']
    safe_executed = results['SAFE']['executed']
    safe_total = safe_blocked + safe_executed
    
    print(f"CRITICAL threats: {critical_blocked}/{critical_total} blocked ({critical_executed} executed)")
    print(f"MEDIUM threats:   {medium_blocked}/{medium_total} blocked ({medium_executed} executed)")
    print(f"SAFE commands:    {safe_executed}/{safe_total} allowed ({safe_blocked} blocked)")
    print()
    
    # Overall assessment
    if critical_executed > 0:
        print("🔴 ASSESSMENT: VULNERABLE - Critical security issues detected!")
        print(f"   {critical_executed} critical threat(s) were NOT blocked.")
    elif medium_executed > critical_total and safe_blocked > 0:
        print("🟡 ASSESSMENT: RESTRICTED - Too restrictive, blocks valid commands.")
    elif medium_executed > 0:
        print("🟡 ASSESSMENT: MODERATE - Medium-level vulnerabilities present.")
    else:
        print("🟢 ASSESSMENT: SECURE - All threats blocked, valid commands allowed.")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if critical_executed > 0:
        print("📌 Immediate action required:")
        print("   • Implement Level 1 (dangerous pattern detection)")
        print("   • Or Level 2 (shlex + shell=False)")
        print()
        print("   See: EXEC_SECURITY_ANALYSIS.md")
    
    # Cleanup
    outside_file.unlink(missing_ok=True)

if __name__ == '__main__':
    run_security_tests()

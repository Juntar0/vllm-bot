#!/usr/bin/env python3
"""
エージェントのツール使用テスト
実際の対話でread/write/execが正しく呼ばれるか検証
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import Agent
from src.vllm_provider import VLLMProvider

def test_agent_tool_usage():
    """Test if agent correctly uses tools in conversation"""
    
    print("=" * 80)
    print("エージェント ツール使用テスト")
    print("=" * 80)
    print()
    
    # Setup
    config = {
        'vllm': {
            'base_url': 'http://localhost:8000/v1',
            'model': 'gpt-oss-medium',  # あなたのモデル名に変更
            'enable_function_calling': True,
            'temperature': 0.0,
            'max_tokens': 2048
        },
        'workspace': {
            'dir': './test_workspace'
        },
        'security': {
            'exec_enabled': True,
            'allowed_commands': ['ls', 'cat', 'echo', 'grep', 'find', 'wc'],
            'exec_timeout': 10
        },
        'system_prompt': {
            'role': 'コーディングアシスタント',
            'tools_note': 'はい、ツールを積極的に使ってタスクを実行してください。'
        }
    }
    
    # Create workspace
    workspace = Path(config['workspace']['dir'])
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Create test agent
    try:
        agent = Agent(
            vllm_config=config['vllm'],
            workspace_config=config['workspace'],
            security_config=config['security'],
            system_prompt_config=config['system_prompt']
        )
    except Exception as e:
        print(f"⚠️  エージェント初期化エラー: {e}")
        print()
        print("vLLMサーバーが起動していない可能性があります。")
        print("以下のコマンドで確認してください：")
        print()
        print("  curl http://localhost:8000/v1/models")
        print()
        return
    
    print("✅ エージェント初期化成功")
    print(f"   モデル: {config['vllm']['model']}")
    print(f"   Function Calling: {config['vllm']['enable_function_calling']}")
    print()
    
    # Test cases: 実際の対話シナリオ
    test_cases = [
        {
            'name': 'ファイル作成',
            'message': 'test.txtというファイルを作って、中身に「Hello World」と書いてください',
            'expected_tools': ['write'],
            'verify': lambda: (workspace / 'test.txt').exists() and 
                            (workspace / 'test.txt').read_text() == 'Hello World'
        },
        {
            'name': 'ファイル読み取り',
            'message': 'test.txtの内容を教えてください',
            'expected_tools': ['read'],
            'verify': None
        },
        {
            'name': 'ファイル編集',
            'message': 'test.txtの中の「World」を「Python」に変更してください',
            'expected_tools': ['edit'],
            'verify': lambda: (workspace / 'test.txt').read_text() == 'Hello Python'
        },
        {
            'name': 'コマンド実行',
            'message': 'ワークスペースにあるファイルをリストアップしてください',
            'expected_tools': ['exec'],
            'verify': None
        },
        {
            'name': '複数ツール',
            'message': 'data.txtというファイルを作って「Line1\\nLine2\\nLine3」と書き込んで、行数を数えてください',
            'expected_tools': ['write', 'exec'],
            'verify': lambda: (workspace / 'data.txt').exists()
        },
    ]
    
    results = {
        'success': 0,
        'partial': 0,
        'failed': 0
    }
    
    for i, test in enumerate(test_cases, 1):
        print(f"{'─' * 80}")
        print(f"テスト {i}: {test['name']}")
        print(f"{'─' * 80}")
        print(f"📝 ユーザー: {test['message']}")
        print()
        
        try:
            # Run agent
            response = agent.chat(test['message'])
            
            print(f"🤖 アシスタント: {response[:200]}...")
            print()
            
            # Check tool usage
            last_iteration = agent.conversation[-1] if agent.conversation else None
            tools_used = []
            
            # Check if any tool was called
            # (This is a simplified check - you might need to track tool calls differently)
            if 'tool' in str(last_iteration).lower():
                print("✅ ツールが呼ばれました")
                
                # Try to identify which tools
                for tool in test['expected_tools']:
                    if tool in str(last_iteration).lower():
                        tools_used.append(tool)
                        print(f"   ✓ {tool}")
                
                if set(tools_used) == set(test['expected_tools']):
                    print(f"✅ 期待されたツールがすべて使われました: {test['expected_tools']}")
                    results['success'] += 1
                    status = 'success'
                elif tools_used:
                    print(f"⚠️  一部のツールのみ使われました: {tools_used} (期待: {test['expected_tools']})")
                    results['partial'] += 1
                    status = 'partial'
                else:
                    print(f"❌ 期待されたツールが使われませんでした: {test['expected_tools']}")
                    results['failed'] += 1
                    status = 'failed'
            else:
                print(f"❌ ツールが呼ばれませんでした (期待: {test['expected_tools']})")
                results['failed'] += 1
                status = 'failed'
            
            # Verify result if function provided
            if test['verify'] and status == 'success':
                try:
                    if test['verify']():
                        print("✅ 実行結果を確認: 正しく完了")
                    else:
                        print("⚠️  実行結果を確認: 期待と異なる")
                        results['success'] -= 1
                        results['partial'] += 1
                except Exception as e:
                    print(f"⚠️  検証エラー: {e}")
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            results['failed'] += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("結果サマリー")
    print("=" * 80)
    print()
    
    total = len(test_cases)
    success_rate = results['success'] / total * 100
    
    print(f"成功: {results['success']}/{total} ({success_rate:.0f}%)")
    print(f"部分成功: {results['partial']}/{total}")
    print(f"失敗: {results['failed']}/{total}")
    print()
    
    if success_rate >= 80:
        print("🟢 評価: 良好 - エージェントはツールを適切に使用できています")
    elif success_rate >= 50:
        print("🟡 評価: 改善の余地あり - ツール使用に課題があります")
    else:
        print("🔴 評価: 要改善 - エージェントがツールを使用できていません")
    
    print()
    print("=" * 80)
    print("トラブルシューティング")
    print("=" * 80)
    print()
    
    if results['failed'] > 0 or results['partial'] > 0:
        print("📌 ツールが使われない場合の原因:")
        print()
        print("1. モデルがFunction Callingに対応していない")
        print("   → config.json で enable_function_calling: false を試す")
        print()
        print("2. システムプロンプトが不十分")
        print("   → src/agent.py の _build_system_prompt() を確認")
        print()
        print("3. モデルの学習データにツール使用例が少ない")
        print("   → Few-shot examples を追加")
        print()
        print("4. temperature が高すぎる")
        print("   → temperature: 0.0 に設定")
        print()
        print("デバッグ方法:")
        print("  DEBUG=1 python3 cli.py")
        print("  → ツールコールの検出状況を確認")
    
    # Cleanup
    import shutil
    if workspace.exists():
        shutil.rmtree(workspace)

if __name__ == '__main__':
    test_agent_tool_usage()

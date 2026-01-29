# デバッグガイド

## ツールが実行されない問題

### 症状

```
You: ワークスペースにあるファイルをリストして

Bot: TOOL_CALL: {
  "name": "exec",
  "args": { "command": "ls -R ." }
}
```

ツール呼び出しが表示されるが、実際には実行されない。

### 解決済み（2026-01-29）

✅ **修正**: 複数行JSONに対応したパーサーを実装

- 改善された正規表現パターン
- ブレースカウンティングフォールバック
- デバッグモード追加

### デバッグモードの使用

```bash
DEBUG=1 python3 cli.py
```

デバッグ出力例：
```
You: ワークスペースにあるファイルをリストして

Bot: TOOL_CALL: { "name": "exec", "args": { "command": "ls" } }

[DEBUG] Iteration 1
[DEBUG] Tool calls found: 1
[DEBUG] Tool calls: [{'name': 'exec', 'args': {'command': 'ls'}}]

Tool execution results:
1. exec
Result: file1.txt
file2.py
...

Bot: 現在のワークスペースには以下のファイルがあります...
```

## パース テスト

ツール呼び出しパーサーをテスト：

```bash
python3 test_tool_parsing.py
```

出力：
```
Testing tool call parsing...

Test Case 1:
============================================================
Input:
TOOL_CALL: {"name": "exec", "args": {"command": "ls"}}

Parsed:
[
  {
    "name": "exec",
    "args": {
      "command": "ls"
    }
  }
]
```

## トラブルシューティング

### 1. ツールが検出されない

**確認**:
```bash
DEBUG=1 python3 cli.py
```

`[DEBUG] Tool calls found: 0` と表示される場合、モデルが正しい形式で出力していない。

**解決策**:
- システムプロンプトを調整
- モデルを変更（gpt-oss-medium → gpt-oss-high）
- `config.json`の`system_prompt.role`を明確化

### 2. JSONパースエラー

**確認**:
```bash
python3 test_tool_parsing.py
```

エラーが出る場合、`src/agent.py`の`_parse_tool_calls()`を確認。

### 3. ツールが部分的に実行される

**原因**: ネストしたオブジェクトや配列

**例**:
```json
TOOL_CALL: {
  "name": "write",
  "args": {
    "path": "config.json",
    "content": "{\"key\": \"value\"}"
  }
}
```

**解決**: ブレースカウンティングアルゴリズムが自動処理

### 4. 複数ツール呼び出し

**サポート**: あり

**例**:
```
TOOL_CALL: {"name": "read", "args": {"path": "file1.txt"}}
TOOL_CALL: {"name": "read", "args": {"path": "file2.txt"}}
```

両方とも検出・実行されます。

## 既知の制限

### 1. 最大イテレーション

デフォルト: 5回

変更方法（`src/agent.py`）:
```python
def chat(self, user_id: int, message: str, max_iterations: int = 10):
```

### 2. JSONエスケープ

エスケープされた引用符は正しく処理されます：
```json
{"content": "He said \"Hello\""}
```

### 3. コメント

JSONコメントは非対応：
```json
// これはエラー
{"name": "exec"}
```

## ログファイル

現在、ログファイルは未実装。

将来の実装予定：
```python
import logging

logging.basicConfig(
    filename='vllm-bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## パフォーマンス

### ツール呼び出しオーバーヘッド

- パース: < 1ms
- 実行: コマンド依存
- ループ: 最大5回

### メモリ使用量

会話履歴は無制限に蓄積されるため、長時間使用時は`/reset`推奨。

## 更新履歴

- **2026-01-29**: 複数行JSON対応、デバッグモード追加
- **2026-01-29**: テストスクリプト追加

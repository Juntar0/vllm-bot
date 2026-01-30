# Debug Mode Guide

## デバッグモード有効化

### 方法1: config.json で設定

```json
{
  "debug": {
    "enabled": true,
    "level": "verbose"
  }
}
```

### 方法2: 実行中に切り替え

```bash
./run.sh

> debug on
✓ Debug enabled

> debug verbose
✓ Debug level: verbose

(コマンド実行)

> debug off
✓ Debug disabled
```

---

## デバッグレベル

### `"basic"` - 基本情報のみ

```
[DEBUG PLANNER] Need tools: True
[DEBUG PLANNER] Tool calls: 1
[DEBUG TOOL_RUNNER] ✓ exec_cmd completed (2583 chars)
```

**表示内容**:
- Planner の判断（ツール呼び出しが必要か）
- 呼び出すツールと数
- ツール実行の成功/失敗

### `"verbose"` - 詳細情報（推奨）

```
[DEBUG PLANNER] --- Input to Planner ---
[DEBUG PLANNER] Request: apt updateしてみて
[DEBUG PLANNER] Facts: [...]

[DEBUG TOOL_RUNNER] --- exec_cmd Full Result ---
{
  "success": true,
  "output": "Get:1 http://archive.ubuntu.com...",
  "error": "",
  "exit_code": 0,
  "duration_sec": 2.45,
  "output_length": 2583
}

[DEBUG RESPONDER] Full output
```

**表示内容**:
- すべての Planner 入出力
- ツール実行の **完全な出力**、エラー、終了コード
- Responder の詳細情報
- State の全詳細

---

## トラブルシューティング

### sudo がパスワード要求するか確認

```bash
# config.json を編集
vi config/config.json

# 以下を追加
"debug": {
  "enabled": true,
  "level": "verbose"
}

./run.sh

> sudo apt updateしてみて
[DEBUG TOOL_RUNNER] --- exec_cmd Full Result ---
{
  "success": true/false,
  "error": "sudo: a password is required"  ← ここに出現
}
```

### コマンド実行の完全な出力を見る

```bash
> debug on
> debug verbose

> apt updateしてみて

[DEBUG TOOL_RUNNER] --- exec_cmd Full Result ---
{
  "output": "... (すべての出力)"
  "error": "... (エラーメッセージ)"
  "exit_code": 0
}
```

### ツール実行時間を確認

```
[DEBUG TOOL_RUNNER] --- exec_cmd Full Result ---
{
  "duration_sec": 2.45  ← 実行時間
}
```

---

## 出力例

### 成功時

```
[DEBUG TOOL_RUNNER] --- exec_cmd Full Result ---
{
  "success": true,
  "output": "Get:1 http://archive.ubuntu.com/ubuntu jammy ...",
  "error": "",
  "exit_code": 0,
  "duration_sec": 1.23,
  "output_length": 2583
}
```

### 失敗時（パスワード要求）

```
[DEBUG TOOL_RUNNER] --- exec_cmd Full Result ---
{
  "success": false,
  "output": "",
  "error": "sudo: a password is required",
  "exit_code": 1,
  "duration_sec": 0.15,
  "output_length": 0
}
```

### パスワードなし設定確認

現在のセットアップでパスワード要求がない場合、output が正常に表示されます。

```
"output": "Get:1 http://archive.ubuntu.com...",
"error": "",
"exit_code": 0
```

---

## クイックスタート

**すぐに verbose デバッグを試す**:

```bash
# config.json を編集
cat config/config.json | sed 's/"level": "basic"/"level": "verbose"/' > config/config.json.tmp
mv config/config.json.tmp config/config.json

# または直接編集
vi config/config.json
# "level": "verbose" に変更

./run.sh

> apt updateしてみて
(詳細なデバッグ出力)
```

---

## コマンドの実装

interactive CLI の `debug` コマンド実装:

```python
# cli.py より
if user_input.lower() == 'debug on':
    agent.debugger.enabled = True
    print("✓ Debug enabled")

if user_input.lower() == 'debug off':
    agent.debugger.enabled = False
    print("✓ Debug disabled")

if user_input.lower().startswith('debug '):
    level = user_input.split()[1]
    agent.debugger.level = level
    print(f"✓ Debug level: {level}")
```

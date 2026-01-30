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
[DEBUG VLLM_API] --- API Request ---
[DEBUG VLLM_API] Messages (2):
[DEBUG VLLM_API]   [0] system: You are a response agent...
[DEBUG VLLM_API]   [1] user: Generate a natural language response...

[DEBUG VLLM_API] --- API Response ---
[DEBUG VLLM_API] Response: apt update が実行され...

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
- **vLLM API リクエスト**（プロンプト内容）
- **vLLM API レスポンス**（LLM の回答）
- すべての Planner 入出力
- ツール実行の **完全な出力**、エラー、終了コード
- Responder の詳細情報
- State の全詳細

---

## API リクエスト・レスポンスの確認

Verbose モードでは vLLM API へのリクエストとレスポンスも表示されます。

### API リクエスト例

```
[DEBUG VLLM_API] --- API Request ---
[DEBUG VLLM_API] URL: http://localhost:8000/v1/chat/completions
[DEBUG VLLM_API] Model: gpt-oss-medium
[DEBUG VLLM_API] Temperature: 0.0
[DEBUG VLLM_API] Max Tokens: 2048
[DEBUG VLLM_API] Messages (2):
[DEBUG VLLM_API]   [0] system: You are a response agent for an OS automation system...
[DEBUG VLLM_API]   [1] user: Generate a natural language response based on the tool results above.
```

### API レスポンス例

```
[DEBUG VLLM_API] --- API Response ---
[DEBUG VLLM_API] Finish Reason: stop
[DEBUG VLLM_API] Response: apt update が実行され、リポジトリ情報が取得されました。
```

### 投げたプロンプトの詳細を見る

```bash
# Verbose モード有効化
vi config/config.json
# "level": "verbose"

./run.sh

> apt updateしてみて

# 出力:
[DEBUG VLLM_API] --- API Request ---
[DEBUG VLLM_API] Messages (N):
[DEBUG VLLM_API]   [0] system: (Planner のシステムプロンプト)
[DEBUG VLLM_API]   [1] user: (ユーザーのリクエスト)

[DEBUG VLLM_API] --- API Response ---
(LLM からの回答)
```

### LLM が何を見ているか確認

```
system メッセージ内容:
- 指示内容
- 環境情報（memory）
- 現在の状態（facts, tasks）
- ツール呼び出しの指示

user メッセージ内容:
- ツール実行結果
- 元のリクエスト
```

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

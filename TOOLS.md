# ツール統合 - vLLMにツールを知らせる方法

## 概要

vLLM Botは**2つの方法**でモデルにツールの存在を知らせます：

1. **Function Calling API** (OpenAI互換)
2. **System Prompt** (テキストベース)

## 方法1: Function Calling API（推奨）

### 仕組み

vLLM APIにツール定義を送信：

```python
POST /v1/chat/completions
{
  "model": "gpt-oss-medium",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "read",
        "description": "Read file contents",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {"type": "string", "description": "File path"},
            "offset": {"type": "integer", "description": "Starting line"},
            "limit": {"type": "integer", "description": "Max lines"}
          },
          "required": ["path"]
        }
      }
    },
    ...
  ]
}
```

### ツール定義の場所

`src/tools.py`:

```python
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read file contents",
            "parameters": {...}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write or create a file",
            "parameters": {...}
        }
    },
    ...
]
```

### モデルのレスポンス（Function Calling対応）

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_123",
          "type": "function",
          "function": {
            "name": "read",
            "arguments": "{\"path\": \"README.md\"}"
          }
        }
      ]
    }
  }]
}
```

### 有効化

`config.json`:

```json
{
  "vllm": {
    "enable_function_calling": true
  }
}
```

**デフォルト**: `true`

---

## 方法2: System Prompt（フォールバック）

Function Calling非対応モデル用のフォールバック。

### システムプロンプトに含まれる内容

```
## Available Tools

- **read(path, offset?, limit?)**: Read file contents
- **write(path, content)**: Write or create a file
- **edit(path, oldText, newText)**: Edit file by replacing exact text
- **exec(command)**: Execute shell command

## Tool Call Format

To call a tool, use this exact format:
```
TOOL_CALL: {
  "name": "tool_name",
  "args": { ... }
}
```

Example:
```
TOOL_CALL: {
  "name": "read",
  "args": { "path": "README.md" }
}
```
```

### モデルのレスポンス（テキストベース）

```
I'll read that file for you.

TOOL_CALL: {
  "name": "read",
  "args": { "path": "README.md" }
}
```

### ツール説明の生成

`src/agent.py`:

```python
def _build_system_prompt(self) -> str:
    # ツール定義から動的に生成
    for tool_def in TOOL_DEFINITIONS:
        func = tool_def["function"]
        name = func["name"]
        desc = func["description"]
        params = func["parameters"]["properties"]
        
        # パラメータリスト生成
        param_list = []
        for param_name, param_info in params.items():
            is_required = param_name in required
            param_str = param_name if is_required else f"{param_name}?"
            param_list.append(param_str)
        
        # フォーマット: - **tool_name(param1, param2?)**: Description
        lines.append(f"- **{name}({', '.join(param_list)})**: {desc}")
```

**重要**: ツール説明は`TOOL_DEFINITIONS`から自動生成されるため、ハードコード不要！

---

## 2つの方法の統合

### 実行フロー

```python
# src/agent.py - chat()メソッド

# 1. Function Calling が有効？
if self.enable_function_calling:
    # vLLM APIにツール定義を送信
    response = self.vllm.chat_completion(conversation, tools=TOOL_DEFINITIONS)
    
    # 2. レスポンスにtool_callsがある？
    function_tool_calls = self.vllm.extract_tool_calls(response)
    if function_tool_calls:
        # OpenAI形式を内部形式に変換
        tool_calls = convert_to_internal_format(function_tool_calls)
    else:
        # フォールバック: テキストパース
        tool_calls = self._parse_tool_calls(assistant_message)
else:
    # Function Calling無効 → テキストパースのみ
    response = self.vllm.chat_completion(conversation, tools=None)
    tool_calls = self._parse_tool_calls(assistant_message)
```

### 利点

1. **モデル互換性**: Function Calling対応/非対応の両方で動作
2. **自動フォールバック**: Function Calling失敗時も正常動作
3. **一元管理**: `TOOL_DEFINITIONS`が唯一の真実の情報源

---

## 設定

### config.json

```json
{
  "vllm": {
    "enable_function_calling": true  // or false
  }
}
```

- `true`: Function Calling API + System Prompt (フォールバック)
- `false`: System Prompt のみ

### いつ無効化すべきか

Function Calling を無効化すべき場合：

1. モデルがFunction Callingに対応していない
2. vLLMサーバーがtoolsパラメータをサポートしていない
3. テキストベースのツール呼び出しを強制したい

---

## ツール追加方法

### 1. ツール実装 (src/tools.py)

```python
def _my_new_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    My new tool implementation
    """
    try:
        result = do_something(args["param"])
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
```

### 2. ToolExecutor.execute()に追加

```python
def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "my_new_tool":
        return self._my_new_tool(args)
    # ...
```

### 3. TOOL_DEFINITIONSに追加

```python
TOOL_DEFINITIONS = [
    # ... existing tools ...
    {
        "type": "function",
        "function": {
            "name": "my_new_tool",
            "description": "Description of my new tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["param"]
            }
        }
    }
]
```

**それだけ！** システムプロンプトは自動更新されます。

---

## デバッグ

### Function Calling が使われているか確認

```bash
DEBUG=1 python3 cli.py
```

```
[DEBUG] Iteration 1
[DEBUG] Function calling format detected: 1 calls
[DEBUG] Tool calls: [{'name': 'read', 'args': {'path': 'file.txt'}}]
```

または：

```
[DEBUG] Iteration 1
[DEBUG] Tool calls found: 1  (text-based parsing)
```

### ツール定義の確認

```python
from src.tools import TOOL_DEFINITIONS
import json
print(json.dumps(TOOL_DEFINITIONS, indent=2))
```

---

## トラブルシューティング

### Function Calling が動作しない

**症状**: ツール定義を送っているのに、モデルが使わない

**原因**:
1. モデルがFunction Callingに対応していない
2. vLLMサーバーがtoolsパラメータを無視している

**解決策**:
```json
{
  "vllm": {
    "enable_function_calling": false
  }
}
```

### テキストパースも動作しない

**症状**: `TOOL_CALL: {...}` が出力されない

**原因**: システムプロンプトが効いていない

**解決策**:
1. `config.json`の`system_prompt.role`を調整
2. より明確な指示を追加
3. モデルを変更（gpt-oss-high等）

---

## まとめ

vLLM Botは**2層のツール検出**を実装：

1. **Function Calling API** (第1層、推奨)
   - vLLM APIに直接ツール定義を送信
   - OpenAI互換形式
   - モデルが構造化された出力を返す

2. **System Prompt** (第2層、フォールバック)
   - テキストベースの説明
   - `TOOL_CALL: {...}` 形式を促す
   - Function Calling非対応モデル用

どちらの場合も、**`TOOL_DEFINITIONS`が唯一の真実の情報源**！

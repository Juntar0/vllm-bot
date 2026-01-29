# vLLM Bot - アーキテクチャ詳細

## ツールコール実行フロー

### 全体フロー図

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Input (CLI)                                         │
│    You: ワークスペースにあるファイルをリストして                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CLIBot.handle_message()                                  │
│    - user_inputを取得                                        │
│    - Agent.chat(user_id, message)を呼び出し                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Agent.chat() - Iteration 1                               │
│                                                              │
│ 3.1 会話履歴取得                                             │
│     conversation = self._get_conversation(user_id)          │
│     └─ システムプロンプト + 過去のメッセージ                    │
│                                                              │
│ 3.2 ユーザーメッセージ追加                                    │
│     conversation.append({                                    │
│       "role": "user",                                        │
│       "content": "ワークスペースにあるファイルをリストして"      │
│     })                                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VLLMProvider.chat_completion()                           │
│                                                              │
│ 4.1 リクエスト構築                                           │
│     POST http://localhost:8000/v1/chat/completions          │
│     {                                                        │
│       "model": "gpt-oss-medium",                             │
│       "messages": [                                          │
│         {"role": "system", "content": "..."},                │
│         {"role": "user", "content": "リストして"}             │
│       ],                                                     │
│       "temperature": 0.7,                                    │
│       "max_tokens": 2048                                     │
│     }                                                        │
│                                                              │
│ 4.2 vLLMサーバーへ送信                                       │
│     response = requests.post(...)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. vLLMサーバー処理                                          │
│    - モデル推論                                              │
│    - レスポンス生成                                          │
│                                                              │
│    返却:                                                     │
│    {                                                         │
│      "choices": [{                                           │
│        "message": {                                          │
│          "content": "TOOL_CALL: {\n  \"name\": \"exec\", ..." │
│        }                                                     │
│      }]                                                      │
│    }                                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Agent._parse_tool_calls()                                │
│                                                              │
│ 6.1 正規表現マッチング                                       │
│     pattern = r'TOOL_CALL:\s*(\{(?:[^{}]|\{[^{}]*\})*\})'  │
│                                                              │
│ 6.2 JSON抽出                                                 │
│     json_str = match.group(1)                                │
│     → '{"name": "exec", "args": {"command": "ls -R ."}}'     │
│                                                              │
│ 6.3 JSONパース                                               │
│     tool_call = json.loads(json_str)                         │
│     → {"name": "exec", "args": {"command": "ls -R ."}}       │
│                                                              │
│ 6.4 検証                                                     │
│     if "name" in tool_call and "args" in tool_call:          │
│       tool_calls.append(tool_call)                           │
│                                                              │
│ 結果: [{"name": "exec", "args": {"command": "ls -R ."}}]    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Agent._execute_tools()                                   │
│                                                              │
│ 7.1 各ツール呼び出しをループ                                  │
│     for call in tool_calls:                                  │
│       name = "exec"                                          │
│       args = {"command": "ls -R ."}                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. ToolExecutor.execute()                                   │
│                                                              │
│ 8.1 ツール判定                                               │
│     if tool_name == "exec":                                  │
│       return self._exec(args)                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. ToolExecutor._exec()                                     │
│                                                              │
│ 9.1 セキュリティチェック                                      │
│     if not self.exec_enabled:                                │
│       return {"error": "disabled"}                           │
│                                                              │
│ 9.2 Allowlistチェック                                        │
│     cmd_name = "ls"                                          │
│     if cmd_name not in self.allowed_commands:                │
│       return {"error": "not allowed"}                        │
│                                                              │
│ 9.3 パス検証                                                 │
│     cwd = str(self.workspace_dir)                            │
│                                                              │
│ 9.4 コマンド実行                                             │
│     result = subprocess.run(                                 │
│       "ls -R .",                                             │
│       shell=True,                                            │
│       cwd=workspace_dir,                                     │
│       capture_output=True,                                   │
│       timeout=30                                             │
│     )                                                        │
│                                                              │
│ 9.5 出力取得                                                 │
│     output = result.stdout                                   │
│     if result.stderr:                                        │
│       output += "\n[stderr]\n" + result.stderr               │
│                                                              │
│ 9.6 出力制限                                                 │
│     if len(output) > 200000:                                 │
│       output = truncate_middle(output)                       │
│                                                              │
│ 9.7 返却                                                     │
│     return {                                                 │
│       "result": output,                                      │
│       "exit_code": 0                                         │
│     }                                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. Agent - ツール結果処理                                   │
│                                                              │
│ 10.1 結果フォーマット                                        │
│      result_lines = [                                        │
│        "Tool execution results:",                            │
│        "1. exec",                                            │
│        "Args: {\"command\": \"ls -R .\"}",                   │
│        "Result: (ファイルリスト)"                             │
│      ]                                                       │
│                                                              │
│ 10.2 会話履歴に追加                                          │
│      conversation.append({                                   │
│        "role": "assistant",                                  │
│        "content": "TOOL_CALL: ..."                           │
│      })                                                      │
│      conversation.append({                                   │
│        "role": "user",                                       │
│        "content": "Tool execution results: ..."              │
│      })                                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 11. Agent.chat() - Iteration 2                              │
│                                                              │
│ 11.1 再度vLLM呼び出し                                        │
│      conversation = [                                        │
│        {"role": "system", "content": "..."},                 │
│        {"role": "user", "content": "リストして"},             │
│        {"role": "assistant", "content": "TOOL_CALL: ..."},   │
│        {"role": "user", "content": "Tool execution..."}      │
│      ]                                                       │
│                                                              │
│      → vLLMが結果を見て最終レスポンス生成                     │
│                                                              │
│ 11.2 レスポンス取得                                          │
│      "現在のワークスペースには以下のファイルがあります..."      │
│                                                              │
│ 11.3 ツールコールチェック                                     │
│      tool_calls = self._parse_tool_calls(response)           │
│      → [] (空)                                               │
│                                                              │
│ 11.4 ツールなし → 最終レスポンス返却                          │
│      conversation.append({                                   │
│        "role": "assistant",                                  │
│        "content": "現在のワークスペースには..."               │
│      })                                                      │
│      return "現在のワークスペースには..."                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 12. CLIBot - ユーザーに表示                                  │
│     print(response)                                          │
│     → "現在のワークスペースには以下のファイルがあります..."      │
└─────────────────────────────────────────────────────────────┘
```

---

## 詳細コードフロー

### 1. エントリーポイント (cli.py)

```python
# cli.py line 45-60
user_input = input("You: ").strip()
response = self.agent.chat(self.user_id, user_input, debug=self.debug)
print(response)
```

### 2. エージェント (src/agent.py)

```python
# agent.py line 135-200
def chat(self, user_id: int, message: str, max_iterations: int = 5, debug: bool = False) -> str:
    conversation = self._get_conversation(user_id)
    conversation.append({"role": "user", "content": message})
    
    for iteration in range(max_iterations):
        # 2.1 vLLM呼び出し
        response = self.vllm.chat_completion(conversation)
        assistant_message = self.vllm.extract_message(response)
        
        # 2.2 ツールコール検出
        tool_calls = self._parse_tool_calls(assistant_message)
        
        if not tool_calls:
            # ツールなし → 終了
            conversation.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        
        # 2.3 ツール実行
        tool_results = self._execute_tools(tool_calls)
        
        # 2.4 結果を会話に追加
        conversation.append({"role": "assistant", "content": assistant_message})
        conversation.append({"role": "user", "content": format_results(tool_results)})
        
        # 2.5 次のイテレーション（最大5回）
```

### 3. ツールパース (src/agent.py)

```python
# agent.py line 80-130
def _parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
    tool_calls = []
    
    # 正規表現でマッチ
    pattern = r'TOOL_CALL:\s*(\{(?:[^{}]|\{[^{}]*\})*\})'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    for match in matches:
        json_str = match.group(1)
        tool_call = json.loads(json_str)
        
        if "name" in tool_call and "args" in tool_call:
            tool_calls.append(tool_call)
    
    return tool_calls
```

### 4. ツール実行 (src/tools.py)

```python
# tools.py line 20-30
def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "read":
        return self._read(args)
    elif tool_name == "write":
        return self._write(args)
    elif tool_name == "edit":
        return self._edit(args)
    elif tool_name == "exec":
        return self._exec(args)
```

### 5. execツール (src/tools.py)

```python
# tools.py line 130-180
def _exec(self, args: Dict[str, Any]) -> Dict[str, Any]:
    command = args["command"]
    
    # Allowlistチェック
    cmd_parts = command.split()
    cmd_name = cmd_parts[0]
    if cmd_name not in self.allowed_commands:
        return {"error": f"Command not allowed: {cmd_name}"}
    
    # 実行
    result = subprocess.run(
        command,
        shell=True,
        cwd=str(self.workspace_dir),
        capture_output=True,
        text=True,
        timeout=self.exec_timeout
    )
    
    # 出力取得
    output = result.stdout
    if result.stderr:
        output += f"\n[stderr]\n{result.stderr}"
    
    # 出力制限
    if len(output) > self.exec_max_output:
        output = truncate_middle(output)
    
    return {
        "result": output,
        "exit_code": result.returncode
    }
```

---

## タイムライン例

実際の実行時間:

```
00:00.000 - User input
00:00.001 - Agent.chat() 開始
00:00.002 - vLLM API リクエスト送信
00:00.500 - vLLM レスポンス受信 (500ms)
00:00.501 - ツールコールパース
00:00.502 - ToolExecutor.execute()
00:00.503 - subprocess.run("ls -R .")
00:00.520 - コマンド完了 (20ms)
00:00.521 - 結果フォーマット
00:00.522 - 会話履歴更新
00:00.523 - 再度vLLM API リクエスト
00:01.000 - vLLM 最終レスポンス受信 (500ms)
00:01.001 - ツールコールなし確認
00:01.002 - 最終レスポンス返却
00:01.003 - ユーザーに表示
```

**合計**: 約1秒（vLLMの推論時間に依存）

---

## 会話履歴の変化

### Iteration 1開始時

```json
[
  {"role": "system", "content": "You are a helpful AI assistant..."},
  {"role": "user", "content": "ワークスペースにあるファイルをリストして"}
]
```

### Iteration 1終了時

```json
[
  {"role": "system", "content": "You are a helpful AI assistant..."},
  {"role": "user", "content": "ワークスペースにあるファイルをリストして"},
  {"role": "assistant", "content": "TOOL_CALL: {\"name\": \"exec\", ...}"},
  {"role": "user", "content": "Tool execution results:\n1. exec\nResult: ..."}
]
```

### Iteration 2終了時（最終）

```json
[
  {"role": "system", "content": "You are a helpful AI assistant..."},
  {"role": "user", "content": "ワークスペースにあるファイルをリストして"},
  {"role": "assistant", "content": "TOOL_CALL: {\"name\": \"exec\", ...}"},
  {"role": "user", "content": "Tool execution results:\n1. exec\nResult: ..."},
  {"role": "assistant", "content": "現在のワークスペースには以下のファイルがあります..."}
]
```

---

## デバッグ出力との対応

```bash
DEBUG=1 python3 cli.py
```

```
You: ワークスペースにあるファイルをリストして

Bot: TOOL_CALL: { "name": "exec", "args": { "command": "ls -R ." } }

[DEBUG] Iteration 1                    ← Agent.chat() ループ開始
[DEBUG] Tool calls found: 1             ← _parse_tool_calls() 結果
[DEBUG] Tool calls: [{'name': 'exec', 'args': {'command': 'ls -R .'}}]

Tool execution results:                 ← _execute_tools() 結果表示
1. exec
Args: {"command": "ls -R ."}
Result: (ファイルリスト)

Bot: 現在のワークスペースには...     ← Iteration 2の最終レスポンス
```

---

## まとめ

1. **ユーザー入力** → CLI
2. **Agent.chat()** → Agentic Loop開始
3. **vLLM呼び出し** → モデル推論
4. **ツールパース** → 正規表現 + JSON
5. **ツール実行** → セキュリティチェック → subprocess
6. **結果追加** → 会話履歴に追記
7. **再度vLLM** → 最終レスポンス生成
8. **返却** → ユーザーに表示

**最大5回のループ**で複雑なタスクも実行可能！

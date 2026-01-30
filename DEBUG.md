# デバッグガイド - DEBUG.md

ユーザ入力からエージェント出力までの全ステップをデバッグ表示できます。

設定は `config.json` で統一管理します。

---

## クイックスタート

### 1. デバッグを有効にする

`config/config.json` を編集：

```json
{
  "debug": {
    "enabled": true,
    "level": "basic"
  }
}
```

### 2. 実行する

```bash
python3 cli_integrated.py "command"
```

### 3. デバッグ出力を確認

```
[DEBUG AGENT_LOOP] === LOOP 1 START ===
[DEBUG PLANNER] --- Input to Planner ---
[DEBUG PLANNER] --- Planner Output ---
[DEBUG TOOL_RUNNER] Executing: read_file
[DEBUG TOOL_RUNNER] ✓ read_file completed
[DEBUG RESPONDER] --- Responder Output ---
```

---

## config.json の debug セクション

```json
{
  "debug": {
    "enabled": false,
    "level": "basic",
    "show_planner": true,
    "show_tool_runner": true,
    "show_responder": true,
    "show_state": true
  }
}
```

### 設定項目

| 項目 | 値 | 説明 |
|------|-----|------|
| `enabled` | `true`/`false` | デバッグ表示のオン/オフ |
| `level` | `"none"`/`"basic"`/`"verbose"` | 詳細度レベル |
| `show_planner` | `true`/`false` | Planner のデバッグ出力 |
| `show_tool_runner` | `true`/`false` | Tool Runner のデバッグ出力 |
| `show_responder` | `true`/`false` | Responder のデバッグ出力 |
| `show_state` | `true`/`false` | State 変更のデバッグ出力 |

---

## デバッグレベル

### Level: "none"
デバッグ出力なし（デフォルト推奨）

### Level: "basic"
主要なステップと決定を表示

**出力例**:
```
[DEBUG AGENT_LOOP] === LOOP 1 START ===
[DEBUG PLANNER] Need tools: true
[DEBUG PLANNER] Reason: Search for Python files
[DEBUG PLANNER] Tool calls: 1
[DEBUG PLANNER]   - find(pattern: *.py, path: .)
[DEBUG TOOL_RUNNER] Executing: find
[DEBUG TOOL_RUNNER] ✓ find completed (1520 chars)
[DEBUG RESPONDER] Is final answer: true
[DEBUG RESPONDER] Response: Found 42 Python files...
```

### Level: "verbose"
詳細な情報を全て表示（開発用）

**出力例**:
```
[DEBUG PLANNER] Request: Find Python files
[DEBUG PLANNER] Facts: [...]
[DEBUG PLANNER] Tasks: [...]
[DEBUG PLANNER] Full output:
{
  "need_tools": true,
  "tool_calls": [...],
  "reason_brief": "...",
  "stop_condition": "..."
}
[DEBUG TOOL_RUNNER] Args: {pattern: *.py, path: .}
[DEBUG RESPONDER] Response: Found 42 Python files in ./workspace...
[DEBUG STATE] Loop 1 state:
  Facts: 5
  Tasks: 2
```

---

## 実行フロー図

```
User Input
  ↓
[DEBUG AGENT] User input: ...

Loop Start
  ↓
[DEBUG AGENT_LOOP] === LOOP 1 START ===
  ↓
Planner Step
  ├─ [DEBUG PLANNER] --- Input to Planner ---
  ├─ [DEBUG PLANNER] Request: ...
  └─ [DEBUG PLANNER] --- Planner Output ---
  ↓
Tool Execution
  ├─ [DEBUG TOOL_RUNNER] Executing: tool1
  ├─ [DEBUG TOOL_RUNNER] ✓ tool1 completed
  └─ [DEBUG TOOL_RUNNER] Executing: tool2
  ↓
Responder Step
  ├─ [DEBUG RESPONDER] --- Input to Responder ---
  ├─ [DEBUG RESPONDER] Original request: ...
  └─ [DEBUG RESPONDER] --- Responder Output ---
  ↓
Decision
  ├─ If done:
  │   [DEBUG AGENT_LOOP] === LOOP 1 END (Stop condition met) ===
  │   [DEBUG AGENT] Final output generated
  │   ↓
  │   Final Response
  │
  └─ If continue:
      [DEBUG AGENT_LOOP] === LOOP 1 END (Continue to next loop) ===
      ↓
      Loop 2...
```

---

## 使用例

### 例1: Basic レベルでデバッグ

```json
{
  "debug": {
    "enabled": true,
    "level": "basic",
    "show_planner": true,
    "show_tool_runner": true,
    "show_responder": true
  }
}
```

実行：
```bash
python3 cli_integrated.py "List Python files"
```

出力：
```
[DEBUG AGENT_LOOP] === LOOP 1 START ===
[DEBUG PLANNER] Need tools: true
[DEBUG PLANNER] Tool calls: 1
[DEBUG PLANNER]   - find(pattern: *.py, path: .)
[DEBUG TOOL_RUNNER] Executing: find
[DEBUG TOOL_RUNNER] ✓ find completed (1520 chars)
[DEBUG RESPONDER] Is final answer: true

<Final response>
```

### 例2: Verbose レベルで詳細確認

```json
{
  "debug": {
    "enabled": true,
    "level": "verbose"
  }
}
```

実行：
```bash
python3 cli_integrated.py "Analyze logs"
```

出力：
```
[DEBUG AGENT_LOOP] === LOOP 1 START ===
[DEBUG PLANNER] --- Input to Planner ---
[DEBUG PLANNER] Request: Analyze logs
[DEBUG PLANNER] Facts: [previous findings]
[DEBUG PLANNER] Tasks: [remaining work]
[DEBUG PLANNER] --- Planner Output ---
[DEBUG PLANNER] Full output:
{
  "need_tools": true,
  "tool_calls": [
    {"tool_name": "find", "args": {"pattern": "*.log"}}
  ],
  "reason_brief": "Search for log files",
  "stop_condition": "found_logs"
}
[DEBUG TOOL_RUNNER] Executing: find
[DEBUG TOOL_RUNNER] Args: {pattern: *.log}
[DEBUG TOOL_RUNNER] ✓ find completed (2048 chars)
[DEBUG RESPONDER] --- Input to Responder ---
[DEBUG RESPONDER] Original request: Analyze logs
[DEBUG RESPONDER] Tool results: 1
[DEBUG RESPONDER] --- Responder Output ---
[DEBUG RESPONDER] Response: Found 5 log files...
[DEBUG STATE] Loop 1 state:
  Facts: 3
  Tasks: 1
[DEBUG AGENT_LOOP] === LOOP 1 END (Continue to next loop) ===
[DEBUG AGENT_LOOP] === LOOP 2 START ===
...
```

### 例3: 特定コンポーネントのみデバッグ

```json
{
  "debug": {
    "enabled": true,
    "level": "basic",
    "show_planner": true,
    "show_tool_runner": false,
    "show_responder": false
  }
}
```

出力：Planner のみ表示

---

## トラブルシューティング

### Q1: デバッグ出力がない

**確認事項**:
1. `config.json` の `debug.enabled` が `true` か確認
2. `level` が `"none"` でないか確認
3. ターミナルに出力が表示されているか確認

### Q2: 出力が多すぎる

**対策**:
```json
{
  "debug": {
    "level": "basic",
    "show_state": false
  }
}
```

State 出力を無効化すると減ります。

### Q3: Planner の詳細を見たい

```json
{
  "debug": {
    "level": "verbose",
    "show_planner": true
  }
}
```

### Q4: 特定の Tool の動作だけ確認したい

```json
{
  "debug": {
    "level": "verbose",
    "show_planner": true,
    "show_tool_runner": true,
    "show_responder": false
  }
}
```

---

## パフォーマンスへの影響

- `enabled: false` → **影響なし** ✓
- `level: "basic"` → **最小限**（推奨）
- `level: "verbose"` → **若干遅い**（開発用）

本番環境では `enabled: false` を推奨。

---

## デバッグ出力の見方

```
[DEBUG <SECTION>] <MESSAGE>
```

### SECTION の種類

| SECTION | 説明 |
|---------|------|
| AGENT | エージェント全体 |
| AGENT_LOOP | ループ制御 |
| PLANNER | LLM ツール選択 |
| TOOL_RUNNER | ツール実行 |
| RESPONDER | LLM 回答生成 |
| STATE | 状態管理 |
| EXECUTION | 実行統計 |

---

## まとめ

デバッグ設定：

```json
{
  "debug": {
    "enabled": true,
    "level": "basic"
  }
}
```

実行：

```bash
python3 cli_integrated.py "request"
```

全ステップの実行フローが表示されます！ 🎯

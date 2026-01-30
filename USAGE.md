# ユーザインタラクション - USAGE.md

## 現在の対話方法

### 方法1: ワンショット CLI（現在の実装）

**1回のリクエストで完全に完結**

```bash
python3 cli_integrated.py "command"
```

**流れ**:
```
ユーザ入力
  ↓
[エージェント処理]
├─ Loop 1: Planner → Tools → Responder
├─ Loop 2: (必要なら)
├─ Loop 3: (必要なら)
└─ Loop N: (最大5ループ)
  ↓
最終結果を表示
  ↓
終了
```

**特徴**:
- ✅ シンプル、わかりやすい
- ✅ 複数ツール呼び出しを自動処理
- ✅ 1つのコマンドで完結
- ❌ 対話不可（1リクエスト1レスポンス）
- ❌ 複数回の質問には向かない

**例**:
```bash
$ python3 cli_integrated.py "Find all Python files and count them"

[処理中...複数ループで自動的にツールを実行...]

Found 42 Python files in workspace
Total lines: 15,420
```

---

## 将来の対話方法（未実装）

### 方法2: 対話型 CLI（推奨案）

**複数の質問を順番に処理**

```bash
python3 cli_interactive.py

> Find Python files
Found 42 Python files

> Count total lines
15,420 lines of code

> Show duplicates
3 duplicate functions found

> exit
```

**利点**:
- ✅ 会話形式での対話
- ✅ 前の回答を context として使用
- ✅ メモリ（long-term memory）を活用
- ✅ 段階的に情報を積み重ねられる

**構造** (未実装):
```python
class InteractiveAgent:
    def __init__(self):
        self.agent = Agent(config)
        self.conversation_history = []
    
    def chat(self, user_input):
        # 過去のメッセージを context に含める
        response = self.agent.run(user_input)
        self.conversation_history.append({
            "user": user_input,
            "agent": response
        })
        return response
```

---

### 方法3: 複数ユーザ対話（未実装）

Telegram/Discord/Slack ボット

```
Telegram: @vllm_bot

User: Find Python files
Bot: Found 42 Python files

User: Count lines
Bot: 15,420 lines

User: Show largest file
Bot: main.py - 2,340 lines
```

---

## 推奨される利用シーン

### シーン1: 単一タスク実行（現在推奨）

```bash
# ✅ ワンショット CLI で OK
python3 cli_integrated.py "Analyze log files and find errors"
```

### シーン2: 複数関連タスク（現在は非効率）

```bash
# ❌ 現在は複数回の CLI 実行が必要
python3 cli_integrated.py "Find Python files"
python3 cli_integrated.py "Count total lines in those files"
python3 cli_integrated.py "List files by size"

# ✅ 将来は対話型 CLI で改善予定
python3 cli_interactive.py
> Find Python files
> Count total lines
> List files by size
```

### シーン3: 複雑な依存関係のあるタスク

```bash
# 各ステップの結果が次のステップに影響
> Find config files
> Parse YAML structure
> Extract database credentials
> Validate connection
> Generate migration script
```

---

## 現在のユーザインタラクション方式

### 入力: ユーザリクエスト

```bash
python3 cli_integrated.py "Find Python files with more than 1000 lines"
```

### 内部処理: 複数ループでの自動対話

エージェント内では複数ループで自動的に対話しています：

```
Loop 1:
  Planner: "Need to find Python files"
  Tools: find *.py → [list of files]
  Responder: "Found 42 Python files"

Loop 2:
  Planner: "Need to check file sizes"
  Tools: wc -l [files] → [line counts]
  Responder: "5 files have >1000 lines"

Loop 3:
  Planner: "Task complete"
  Tools: (none)
  Responder: "Final answer ready"
  STOP
```

### 出力: 最終結果

```
Found 5 Python files with more than 1000 lines:
- main.py: 2,340 lines
- utils.py: 1,560 lines
- config.py: 1,245 lines
- ...
```

---

## ユーザの視点

### 現在（ワンショット CLI）

```
ユーザの労力: 最小
複雑度: シンプル

$ python3 cli_integrated.py "Find Python files"
✓ 結果を得る
```

### 将来（対話型）

```
ユーザの労力: 中程度
複雑度: 自然言語対話

$ python3 cli_interactive.py
> Find Python files
✓ 結果を得る
> Count lines
✓ 結果を得る
> Find largest
✓ 結果を得る
> exit
```

---

## デバッグ時の対話

デバッグを有効にすると、**エージェント内部での対話が見える**：

```bash
# config.json
{
  "debug": { "enabled": true, "level": "basic" }
}

# 実行
$ python3 cli_integrated.py "Find Python files"

[DEBUG PLANNER] Planner: "I need to find Python files"
  → Tool: find *.py

[DEBUG TOOL_RUNNER] Executed: find *.py
  → Result: 42 files

[DEBUG RESPONDER] Responder: "Found 42 Python files"

[DEBUG PLANNER] Planner: "Task complete, no more tools needed"

[DEBUG RESPONDER] Responder: "Final answer: Found 42 Python files"
  → STOP
```

---

## 推奨される使用方法

### 今すぐ使う（ワンショット CLI）

```bash
# シンプルなタスク実行
python3 cli_integrated.py "List all config files"

# 複雑なタスク実行（複数ループで自動処理）
python3 cli_integrated.py "Find and analyze large log files"

# デバッグ付き実行
# config.json で enabled:true にして
python3 cli_integrated.py "command"
```

### 今後の改善案

```bash
# 対話型 CLI（実装予定）
python3 cli_interactive.py

# Telegram ボット（実装予定）
@vllm_agent_bot に話しかける

# Web UI（実装予定）
http://localhost:8000/ にアクセス
```

---

## まとめ

| 方法 | 実装 | 利用可能 | 用途 |
|------|------|--------|------|
| **ワンショット CLI** | ✅ | 今すぐ | 単一タスク |
| **対話型 CLI** | ❌ | 計画中 | 複数関連タスク |
| **Telegram ボット** | ❌ | 計画中 | スマートフォン |
| **Web UI** | ❌ | 計画中 | ブラウザ |

**現在**: ワンショット CLI で十分に機能
**今後**: 対話型インタフェースを検討予定

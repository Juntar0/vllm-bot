# vLLM Bot - Interactive Agent

**対話型エージェント** - 複数のターンで会話しながりながらタスクを実行します。

```bash
$ python3 cli.py

> Find all Python files
Found 42 Python files in ./workspace

> Count total lines in them
15,420 lines of code

> Show files larger than 1000 lines
5 files:
- main.py: 2,340 lines
- utils.py: 1,560 lines
- config.py: 1,245 lines
- ...

> exit
Goodbye! 👋
```

---

## クイックスタート

### 1. セットアップ

```bash
cd ~/clawd/vllm-bot
mkdir -p workspace data

# config/config.json を確認・編集
vi config/config.json
```

### 2. 実行

```bash
python3 cli.py
```

### 3. 対話開始

```
> あなたのリクエスト
エージェントの回答

> 次のリクエスト
エージェントの回答

> exit
```

---

## コマンド

対話中に以下が使用できます：

```
help              - ヘルプを表示
clear             - 会話履歴をクリア（新規開始）
debug on/off      - デバッグ出力の切り替え
config            - 現在の設定を表示
exit / quit       - 終了
```

**例**:
```
> debug on
✓ Debug enabled

> Find Python files
[DEBUG PLANNER] ...
[DEBUG TOOL_RUNNER] ...
Found 42 files

> debug off
✓ Debug disabled

> Count lines
15,420 lines
```

---

## 設定 (config/config.json)

```json
{
  "vllm": {
    "base_url": "http://localhost:8000/v1",
    "model": "gpt-oss-medium"
  },
  "workspace": {
    "dir": "./workspace"
  },
  "security": {
    "allowed_commands": ["ls", "cat", "grep", "find", "echo", "wc"],
    "timeout_sec": 30
  },
  "debug": {
    "enabled": false,
    "level": "basic"
  },
  "agent": {
    "max_loops": 5
  }
}
```

詳細は `CONFIG.md` を参照。

---

## デバッグ

実行中に内部処理を見たい場合：

```
> debug on

> Find Python files
[DEBUG PLANNER] Need tools: true
[DEBUG PLANNER] Tool calls: 1
[DEBUG TOOL_RUNNER] Executing: find
[DEBUG TOOL_RUNNER] ✓ find completed
[DEBUG RESPONDER] Response: Found 42 files

> debug off
```

詳細は `DEBUG.md` を参照。

---

## アーキテクチャ

```
┌──────────────────────────────────┐
│     Interactive Chat Loop        │
├──────────────────────────────────┤
│ User: > Find Python files        │
│   ↓                              │
│ [Agent Processing]               │
│ ├─ Planner (LLM)                 │
│ ├─ Tool Runner (Host)            │
│ └─ Responder (LLM)               │
│   ↓                              │
│ Agent: Found 42 files            │
│   ↓                              │
│ User: > Count lines              │
│   ↓                              │
│ [Agent Processing]               │
│   ↓                              │
│ Agent: 15,420 lines              │
│   ↓                              │
│ User: > exit                     │
└──────────────────────────────────┘
```

---

## 機能

### ✅ 実装済み

- **対話型インタフェース** - 複数ターンでの会話
- **複数ループ処理** - 最大5ループで複雑なタスク対応
- **セキュリティ** - パス制限、コマンド allowlist
- **メモリ** - 長期記憶で前の回答を活用
- **デバッグ** - 内部処理を可視化
- **設定管理** - JSON ベースの統一設定

### 🔧 ツール

- `list_dir` - ファイル/ディレクトリ一覧
- `read_file` - ファイル読み込み
- `write_file` - ファイル作成/上書き
- `edit_file` - テキスト置換
- `exec_cmd` - シェルコマンド実行
- `grep` - ファイル検索

---

## 使用例

### 例1: ファイル操作

```
> List Python files
Found 42 Python files

> Count total lines
15,420 lines

> Find largest file
main.py: 2,340 lines
```

### 例2: ログ分析

```
> Find error logs
Found 3 error.log files

> Count errors
127 errors total

> Show errors by type
- DatabaseError: 45
- NetworkError: 52
- TimeoutError: 30
```

### 例3: デバッグ付き実行

```
> debug on
✓ Debug enabled

> Find files
[DEBUG PLANNER] Need tools: true
[DEBUG TOOL_RUNNER] Executing: find
Found 42 files

> debug off
✓ Debug disabled
```

---

## 設定値変更

config.json を編集して設定を変更：

```json
{
  "workspace": {
    "dir": "/"                      // システム全体にアクセス
  },
  "security": {
    "allowed_commands": [],         // すべてのコマンド実行可
    "timeout_sec": 60               // タイムアウト 60 秒
  },
  "debug": {
    "enabled": true,                // デバッグデフォルト有効
    "level": "verbose"              // 詳細情報を表示
  }
}
```

---

## ドキュメント

| ファイル | 内容 |
|---------|------|
| `CONFIG.md` | 設定オプション詳細 |
| `DEBUG.md` | デバッグシステム詳細 |
| `USAGE.md` | ユーザインタラクション |
| `README_COMPLETE.md` | 完全な技術ドキュメント |

---

## トラブルシューティング

### vLLM に接続できない

```
❌ Error: Failed to connect to vLLM API

対策:
1. vLLM サーバが起動しているか確認
2. config.json の base_url を確認
3. ファイアウォール設定を確認
```

### コマンドが実行されない

```
❌ Command not allowed: rm

対策:
config.json の allowed_commands に追加：
"allowed_commands": ["ls", "cat", "rm"]
```

---

## ライセンス

MIT

---

## サポート

問題が発生した場合：

1. `debug on` で内部処理を確認
2. `config` で現在の設定を確認
3. ドキュメントを参照（CONFIG.md, DEBUG.md）

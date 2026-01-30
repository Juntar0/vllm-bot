# vLLM Bot - Interactive Agent

対話型エージェント。複数ターンで会話しながらタスク実行。

## クイックスタート

```bash
# セットアップ
mkdir -p workspace data
vi config/config.json  # 設定を確認

# 実行
python3 cli.py
```

## 使用方法

```
> Find Python files
Found 42 Python files

> Count total lines
15,420 lines

> Show largest file
main.py: 2,340 lines

> debug on
✓ Debug enabled

> Find errors
[DEBUG PLANNER] Need tools: true
[DEBUG TOOL_RUNNER] Executing: grep
Found 12 errors

> exit
Goodbye! 👋
```

## コマンド

| コマンド | 動作 |
|---------|------|
| `help` | ヘルプ表示 |
| `debug on/off` | デバッグ切り替え |
| `clear` | 会話クリア |
| `config` | 設定表示 |
| `exit/quit` | 終了 |

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
    "allowed_commands": ["ls", "cat", "grep", "find", "wc"],
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

## セキュリティ設定

### workspace.dir
- `./workspace` - ワークスペース内のみ（デフォルト）
- `/` - システム全体

### allowed_commands
許可するコマンドのリスト：
```json
"allowed_commands": ["ls", "cat", "grep", "find", "wc", "head", "tail"]
```

### その他
- `timeout_sec` - コマンド実行タイムアウト（秒）
- `max_output_size` - 出力サイズ制限（文字数）

## デバッグ

実行中にデバッグを有効化：

```
> debug on
✓ Debug enabled

> Find files
[DEBUG PLANNER] ...
[DEBUG TOOL_RUNNER] ...
[DEBUG RESPONDER] ...

> debug off
✓ Debug disabled
```

**レベル**: `"none"` / `"basic"` / `"verbose"`

## 機能

### ツール
- `list_dir` - ファイル一覧
- `read_file` - ファイル読込
- `write_file` - ファイル作成
- `edit_file` - テキスト置換
- `exec_cmd` - シェルコマンド実行
- `grep` - ファイル検索

### 特徴
- **多ターン対話** - 複数質問を順番に処理
- **自動ループ処理** - 複雑なタスクは最大5ループで自動処理
- **メモリ** - 前の回答をコンテキストに使用
- **セキュリティ** - パス制限、コマンド制限、リソース制限
- **ログ記録** - 監査ログを自動記録

## トラブルシューティング

### vLLM に接続できない

```
config.json の base_url を確認：
"base_url": "http://localhost:8000/v1"
```

### コマンドが実行されない

```json
config.json の allowed_commands に追加：
"allowed_commands": ["ls", "cat", "grep", "rm"]
```

### 出力が見えない

```
> debug on
で内部処理を確認
```

## テスト

```bash
python3 test_integration.py
python3 test_agent_loop.py
```

## ファイル構成

```
vllm-bot/
├── cli.py                 # メインプログラム
├── config/config.json     # 設定ファイル
├── src/
│   ├── agent.py          # 統合エージェント
│   ├── agent_loop.py     # ループ制御
│   ├── planner.py        # ツール選択
│   ├── tool_runner.py    # ツール実行
│   ├── responder.py      # 回答生成
│   ├── memory.py         # 長期記憶
│   ├── state.py          # 短期状態
│   ├── debugger.py       # デバッグ
│   └── ...
├── workspace/            # 作業ディレクトリ
├── data/                 # メモリ・ログ
└── test_*.py            # テスト
```

## ライセンス

MIT

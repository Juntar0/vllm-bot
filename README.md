# vLLM Bot - Interactive Agent

対話型エージェント。複数ターンで会話しながらタスク実行。

## クイックスタート

```bash
# セットアップ
./setup.sh

# 実行
./run.sh
```

## 使用方法

**シンプルで見やすい出力形式**:

```
> ディレクトリを見して
• bin/
• boot/
• cdrom/
• dev/
• etc/
(清潔なリスト形式)

> Python ファイルを探して
• src/agent.py
• src/planner.py
• src/responder.py
• test/test_integration.py
(箇条書きで表示)

> main.py の行数を数えて
2,340 行

> debug on
✓ Debug enabled

> 今のディレクトリをみして
[DEBUG PLANNER] Need tools: true
[DEBUG TOOL_RUNNER] Executing: list_dir
• bin/
• boot/
...

> exit
Goodbye! 👋
```

**出力形式の特徴**:
- ✅ シンプルで読みやすい
- ✅ 箇条書きで情報整理
- ✅ 冗長な説明なし
- ✅ 日本語・英語両対応

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

- **vLLM エラー**: [VLLM_TROUBLESHOOT.md](VLLM_TROUBLESHOOT.md)
- **デバッグモード**: [DEBUG_MODE.md](DEBUG_MODE.md)

### vLLM に接続できない

```
config.json の base_url を確認：
"base_url": "http://localhost:8000/v1"

詳細は VLLM_TROUBLESHOOT.md を参照
```

### コマンドが実行されない

```json
config.json の allowed_commands に追加：
"allowed_commands": []  # 全コマンド許可
```

### ツール実行・API リクエストの詳細を見たい

```bash
vi config/config.json
# "level": "verbose" に変更

./run.sh

> apt updateしてみて

# vLLM API リクエスト
[DEBUG VLLM_API] --- API Request ---
[DEBUG VLLM_API] Messages (2):
[DEBUG VLLM_API]   [0] system: You are a response agent...
[DEBUG VLLM_API]   [1] user: Generate a response...

# ツール実行結果
[DEBUG TOOL_RUNNER] --- exec_cmd Full Result ---
{
  "output": "Get:1 http://...",
  "error": "",
  "exit_code": 0
}

# vLLM API レスポンス
[DEBUG VLLM_API] --- API Response ---
[DEBUG VLLM_API] Response: apt update が実行され...
```

## テスト

```bash
# 統合テスト
python3 test/test_integration.py

# 個別テスト
python3 test/test_agent_loop.py
python3 test/test_planner.py
python3 test/test_responder.py
python3 test/test_tool_runner.py
```

## ファイル構成

```
vllm-bot/
├── cli.py                 # メインプログラム
├── config/config.json     # 設定ファイル
├── src/                   # ソースコード
│   ├── agent.py          # 統合エージェント
│   ├── agent_loop.py     # ループ制御
│   ├── planner.py        # ツール選択
│   ├── tool_runner.py    # ツール実行
│   ├── responder.py      # 回答生成
│   ├── memory.py         # 長期記憶
│   ├── state.py          # 短期状態
│   └── ...
├── test/                  # テスト
│   ├── test_integration.py
│   ├── test_agent_loop.py
│   ├── test_planner.py
│   ├── test_responder.py
│   ├── test_tool_runner.py
│   ├── test_*.py
│   └── test_data/
├── workspace/            # 作業ディレクトリ
└── data/                 # メモリ・ログ
```

## ライセンス

MIT

# vLLM Bot

**シンプルなAIボット** - vLLM (`v1/chat/completions`) + Telegram統合

Clawdbotの設計を参考にした最小構成のボット実装。

## 特徴

- ✅ vLLM (`v1/chat/completions`) のみ使用
- ✅ ツール実行（read/write/edit/exec）
- ✅ Telegram統合
- ✅ 会話履歴管理
- ✅ セキュリティ（コマンドallowlist、パストラバーサル防止）

## アーキテクチャ

```
Telegram User
      ↓
TelegramBot (telegram_bot.py)
      ↓
Agent (agent.py)
  ├─ VLLMProvider (vllm_provider.py)
  └─ ToolExecutor (tools.py)
      ├─ read
      ├─ write
      ├─ edit
      └─ exec
```

### データフロー

```
User Message
    ↓
Agent.chat()
    ↓
vLLM API (v1/chat/completions)
    ↓
Tool Call検出（テキストパース）
    ↓
ToolExecutor.execute()
    ↓
結果をconversationに追加
    ↓
次のvLLM呼び出し（最大5回）
    ↓
最終レスポンス
```

## セットアップ

### 1. 依存関係インストール

```bash
cd ~/clawd/vllm-bot
pip install -r requirements.txt
```

### 2. 設定ファイル作成

```bash
cp config/config.example.json config/config.json
```

### 3. 設定を編集

`config/config.json`:

```json
{
  "vllm": {
    "base_url": "http://localhost:8000/v1",
    "model": "meta-llama/Llama-2-70b-chat-hf",
    "api_key": "dummy"
  },
  
  "telegram": {
    "token": "YOUR_TELEGRAM_BOT_TOKEN",
    "allowed_users": [123456789]  // あなたのTelegram user ID
  }
}
```

**Telegram Bot Token取得方法**:
1. Telegramで [@BotFather](https://t.me/botfather) と会話
2. `/newbot` コマンドでボット作成
3. トークンをコピーして設定ファイルに貼り付け

**User ID確認方法**:
1. [@userinfobot](https://t.me/userinfobot) と会話
2. あなたのIDが表示される

### 4. vLLMサーバー起動（別ターミナル）

```bash
# vLLMサーバーが別で動作していることを想定
# 接続先を config.json の base_url で指定
```

**モデル設定**:

`config/config.json`でモデルリストを設定：
```json
{
  "vllm": {
    "available_models": [
      "gpt-oss-low",
      "gpt-oss-medium",
      "gpt-oss-high"
    ],
    "default_model_index": 1
  }
}
```

モデルはvLLMサーバー側で提供されているものと一致させる必要があります。

### 5. ボット起動

**CLI版（推奨）**:
```bash
python cli.py
```

**Telegram版**:
```bash
python main.py
```

## 使用方法

### CLI（コマンドライン）で会話 ⭐

```bash
python cli.py
```

**起動時の流れ**:
1. モデル選択（config.jsonの`available_models`から選択）
2. REPLが起動
3. メッセージを入力して会話

**コマンド**:
- `/reset` - 会話履歴リセット
- `/help` - ヘルプ表示
- `/exit` - 終了（Ctrl+Cでも可）

**例**:
```
You: ワークスペースにあるファイルをリストして

Bot: TOOL_CALL: {
  "name": "exec",
  "args": { "command": "ls -la" }
}

Tool execution results:
...

Bot: 現在のワークスペースには以下のファイルがあります：
- README.md
- cli.py
- main.py
```

### Telegramで会話

1. ボットを検索して開始
2. メッセージを送信

**例**:

```
You: ワークスペースにあるファイルをリストして

Bot: TOOL_CALL: {
  "name": "exec",
  "args": { "command": "ls -la" }
}

Tool execution results:
1. exec
Result: total 32
drwxr-xr-x 5 user user 4096 ...
...

現在のワークスペースには以下のファイルがあります：
- README.md
- main.py
- src/
```

### コマンド

- `/start` - ウェルカムメッセージ
- `/reset` - 会話履歴リセット

## ツール

### 1. read

ファイル読み取り

```
TOOL_CALL: {
  "name": "read",
  "args": { "path": "README.md" }
}
```

### 2. write

ファイル作成・上書き

```
TOOL_CALL: {
  "name": "write",
  "args": {
    "path": "test.txt",
    "content": "Hello, World!"
  }
}
```

### 3. edit

ファイル編集（完全一致置換）

```
TOOL_CALL: {
  "name": "edit",
  "args": {
    "path": "test.txt",
    "oldText": "Hello",
    "newText": "Hi"
  }
}
```

### 4. exec

コマンド実行

```
TOOL_CALL: {
  "name": "exec",
  "args": { "command": "ls -la" }
}
```

## ツール統合

### vLLMにツールを知らせる方法

このボットは**2つの方法**でモデルにツールの存在を伝えます：

#### 1. Function Calling API（推奨）

vLLM APIにツール定義を送信：

```json
POST /v1/chat/completions
{
  "model": "gpt-oss-medium",
  "messages": [...],
  "tools": [
    {"type": "function", "function": {"name": "read", ...}},
    {"type": "function", "function": {"name": "write", ...}},
    ...
  ]
}
```

**有効化**（デフォルト）:
```json
{
  "vllm": {
    "enable_function_calling": true
  }
}
```

#### 2. System Prompt（フォールバック）

Function Calling非対応モデル用。システムプロンプトにツール説明を含めます。

**無効化**:
```json
{
  "vllm": {
    "enable_function_calling": false
  }
}
```

### ツール定義の場所

すべてのツールは `src/tools.py` の `TOOL_DEFINITIONS` で定義されます。

新しいツールを追加すると、自動的に：
- vLLM API に送信される
- システムプロンプトに追加される

詳細は `TOOLS.md` を参照してください。

## セキュリティ

### コマンドallowlist

`config.json`の`security.allowed_commands`で許可するコマンドを制限：

```json
{
  "security": {
    "exec_enabled": true,
    "allowed_commands": [
      "ls", "cat", "pwd", "echo", "grep", "find"
    ]
  }
}
```

### パストラバーサル防止

すべてのファイル操作は`workspace_dir`内に制限される。

`../../../etc/passwd`のようなパスは拒否される。

### ユーザー制限

`telegram.allowed_users`で使用可能なユーザーを制限：

```json
{
  "telegram": {
    "allowed_users": [123456789, 987654321]
  }
}
```

空の配列 or 未設定 = すべてのユーザーを許可（非推奨）

## カスタマイズ

### システムプロンプト

`config/config.json`の`system_prompt`セクションを編集：

```json
{
  "system_prompt": {
    "role": "You are a coding assistant specialized in Python.",
    "workspace_note": "Your workspace: {workspace_dir}",
    "tools_note": "Available tools: read, write, edit, exec"
  }
}
```

### ワークスペース

デフォルトは`./workspace`。変更可能：

```json
{
  "workspace": {
    "dir": "/path/to/your/workspace"
  }
}
```

## デバッグ

### デバッグモードの有効化

ツールが正しく検出・実行されているか確認：

```bash
DEBUG=1 python cli.py
```

**デバッグ出力例**:
```
You: ワークスペースにあるファイルをリストして

Bot: TOOL_CALL: { "name": "exec", "args": { "command": "ls" } }

[DEBUG] Iteration 1
[DEBUG] Tool calls found: 1
[DEBUG] Tool calls: [{'name': 'exec', 'args': {'command': 'ls'}}]

Tool execution results:
...
```

### ツールパーサーのテスト

```bash
python3 test_tool_parsing.py
```

様々な形式のツール呼び出しをテストできます。

詳細は `DEBUGGING.md` を参照してください。

## トラブルシューティング

### vLLM接続エラー

```
Error: vLLM API error: ...
```

**解決策**:
1. vLLMサーバーが起動しているか確認
2. `base_url`が正しいか確認
3. モデル名が正しいか確認

### Telegram接続エラー

```
Error: telegram.error.InvalidToken
```

**解決策**:
1. トークンが正しいか確認
2. スペースや改行が入っていないか確認

### ツールが動作しない

**Function Calling非対応モデルの場合**:

モデルがfunction callingに対応していない場合、テキストベースのツール呼び出し形式を使用：

```
TOOL_CALL: { "name": "read", "args": { "path": "file.txt" } }
```

LLMがこの形式を出力するようにプロンプトで誘導される。

## 開発ログ

このボットは以下の設計原則に基づいて実装：

1. **最小構成**: Clawdbotの複雑さを排除
2. **vLLM専用**: `v1/chat/completions`のみ使用
3. **セキュリティファースト**: allowlist、パス検証
4. **シンプルなルーティング**: user_id → conversation

**参考にしたClawdbotの設計**:
- 動的システムプロンプト生成
- ツール抽象化（read/write/edit/exec）
- サンドボックス（パス検証）
- 会話履歴管理

## ライセンス

MIT

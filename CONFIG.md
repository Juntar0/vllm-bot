# vLLM Bot - 設定リファレンス

## config.json 完全リファレンス

### 基本構造

```json
{
  "vllm": { ... },
  "telegram": { ... },
  "workspace": { ... },
  "security": { ... },
  "system_prompt": { ... }
}
```

---

## vLLM設定

### available_models

**型**: `string[]`  
**必須**: はい  
**説明**: 選択可能なモデルのリスト

```json
{
  "vllm": {
    "available_models": [
      "gpt-oss-low",
      "gpt-oss-medium",
      "gpt-oss-high"
    ]
  }
}
```

**カスタム例**:
```json
{
  "vllm": {
    "available_models": [
      "llama-3-70b-instruct",
      "mixtral-8x7b-instruct",
      "qwen-72b-chat"
    ]
  }
}
```

**注意**: vLLMサーバー側で提供されているモデル名と一致させる必要があります。

### default_model_index

**型**: `number`  
**必須**: いいえ  
**デフォルト**: `0`  
**説明**: デフォルトで選択されるモデルのインデックス（0始まり）

```json
{
  "vllm": {
    "available_models": ["model-a", "model-b", "model-c"],
    "default_model_index": 1  // model-b がデフォルト
  }
}
```

### base_url

**型**: `string`  
**必須**: はい  
**説明**: vLLMサーバーのベースURL

```json
{
  "vllm": {
    "base_url": "http://localhost:8000/v1"
  }
}
```

**リモートサーバーの例**:
```json
{
  "vllm": {
    "base_url": "http://192.168.1.100:8000/v1"
  }
}
```

### model

**型**: `string`  
**必須**: いいえ  
**説明**: デフォルトモデル（CLI版では起動時に上書きされる）

### api_key

**型**: `string`  
**必須**: いいえ  
**デフォルト**: `"dummy"`  
**説明**: APIキー（CLI版では常に`"dummy"`）

### temperature

**型**: `number`  
**必須**: いいえ  
**デフォルト**: `0.7`  
**範囲**: `0.0 - 2.0`  
**説明**: サンプリング温度（低いほど決定的、高いほどランダム）

```json
{
  "vllm": {
    "temperature": 0.3  // より決定的
  }
}
```

### max_tokens

**型**: `number`  
**必須**: いいえ  
**デフォルト**: `2048`  
**説明**: 最大トークン数（レスポンス長の上限）

```json
{
  "vllm": {
    "max_tokens": 4096  // より長いレスポンス
  }
}
```

### enable_function_calling

**型**: `boolean`  
**必須**: いいえ  
**デフォルト**: `true`  
**説明**: Function Calling API（OpenAI互換）を使用するか

```json
{
  "vllm": {
    "enable_function_calling": true  // Function Calling使用
  }
}
```

**`true`の場合**:
- vLLM APIに`tools`パラメータを送信
- モデルが構造化された`tool_calls`を返す
- フォールバックでテキストパースも実行

**`false`の場合**:
- システムプロンプトのみでツール説明
- テキストベースの`TOOL_CALL: {...}`形式を使用

詳細は `TOOLS.md` を参照。

---

## Workspace設定

### dir

**型**: `string`  
**必須**: いいえ  
**デフォルト**: `"./workspace"`  
**説明**: 作業ディレクトリのパス

```json
{
  "workspace": {
    "dir": "/home/user/projects/my-workspace"
  }
}
```

### max_file_size_mb

**型**: `number`  
**必須**: いいえ  
**デフォルト**: `10`  
**説明**: ファイル最大サイズ（MB）

```json
{
  "workspace": {
    "max_file_size_mb": 50
  }
}
```

---

## Security設定

### exec_enabled

**型**: `boolean`  
**必須**: いいえ  
**デフォルト**: `true`  
**説明**: `exec`ツールの有効化

```json
{
  "security": {
    "exec_enabled": false  // コマンド実行を無効化
  }
}
```

### exec_timeout

**型**: `number`  
**必須**: いいえ  
**デフォルト**: `30`  
**説明**: コマンド実行のタイムアウト（秒）

```json
{
  "security": {
    "exec_timeout": 60  // 1分
  }
}
```

### exec_max_output

**型**: `number`  
**必須**: いいえ  
**デフォルト**: `200000`  
**説明**: コマンド出力の最大文字数

```json
{
  "security": {
    "exec_max_output": 100000  // 10万文字
  }
}
```

### allowed_commands

**型**: `string[]`  
**必須**: いいえ  
**デフォルト**: `[]` (制限なし)  
**説明**: 許可するコマンドのリスト（空の場合は制限なし）

```json
{
  "security": {
    "allowed_commands": [
      "ls",
      "cat",
      "grep",
      "find",
      "git"
    ]
  }
}
```

**制限なし（非推奨）**:
```json
{
  "security": {
    "allowed_commands": []
  }
}
```

---

## System Prompt設定

### role

**型**: `string`  
**必須**: いいえ  
**デフォルト**: `"You are a helpful AI assistant..."`  
**説明**: システムプロンプトの役割定義

```json
{
  "system_prompt": {
    "role": "You are a Python coding expert specializing in FastAPI and async programming."
  }
}
```

### workspace_note

**型**: `string`  
**必須**: いいえ  
**説明**: ワークスペースに関する注記（`{workspace_dir}`プレースホルダー使用可能）

```json
{
  "system_prompt": {
    "workspace_note": "Your workspace is located at: {workspace_dir}"
  }
}
```

### tools_note

**型**: `string`  
**必須**: いいえ  
**説明**: ツールに関する注記

```json
{
  "system_prompt": {
    "tools_note": "You have access to file operations and shell commands."
  }
}
```

---

## Telegram設定（Telegram版のみ）

### token

**型**: `string`  
**必須**: Telegram版では必須  
**説明**: Telegram Bot Token

```json
{
  "telegram": {
    "token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
  }
}
```

### allowed_users

**型**: `number[]`  
**必須**: いいえ  
**デフォルト**: `[]` (全ユーザー許可)  
**説明**: 使用を許可するTelegram User IDのリスト

```json
{
  "telegram": {
    "allowed_users": [123456789, 987654321]
  }
}
```

**全ユーザー許可（非推奨）**:
```json
{
  "telegram": {
    "allowed_users": []
  }
}
```

---

## 設定例

### CLI専用（最小構成）

```json
{
  "vllm": {
    "base_url": "http://localhost:8000/v1",
    "available_models": ["gpt-oss-medium"],
    "default_model_index": 0,
    "api_key": "dummy",
    "temperature": 0.7,
    "max_tokens": 2048
  },
  
  "workspace": {
    "dir": "./workspace"
  },
  
  "security": {
    "exec_enabled": true,
    "allowed_commands": ["ls", "cat", "pwd"]
  },
  
  "system_prompt": {
    "role": "You are a helpful AI assistant."
  }
}
```

### 開発用（コマンド制限緩和）

```json
{
  "vllm": {
    "base_url": "http://localhost:8000/v1",
    "available_models": [
      "gpt-oss-low",
      "gpt-oss-medium",
      "gpt-oss-high"
    ],
    "default_model_index": 1
  },
  
  "security": {
    "allowed_commands": [
      "ls", "cat", "pwd", "grep", "find",
      "git", "python", "python3", "node", "npm", "pip"
    ]
  }
}
```

### 本番用（セキュリティ重視）

```json
{
  "vllm": {
    "base_url": "http://production-server:8000/v1",
    "available_models": ["production-model"],
    "default_model_index": 0
  },
  
  "security": {
    "exec_enabled": true,
    "exec_timeout": 10,
    "allowed_commands": ["ls", "cat", "grep"]
  },
  
  "telegram": {
    "allowed_users": [123456789]
  }
}
```

---

## トラブルシューティング

### モデルが見つからない

**エラー**: `Model not found: your-model`

**解決策**:
1. vLLMサーバーで該当モデルが起動しているか確認
2. `available_models`のモデル名が正確か確認

### コマンドが実行できない

**エラー**: `Command not allowed: git`

**解決策**:
`allowed_commands`に追加：
```json
{
  "security": {
    "allowed_commands": ["ls", "cat", "git"]
  }
}
```

### 接続エラー

**エラー**: `Connection refused`

**解決策**:
1. `base_url`が正しいか確認
2. vLLMサーバーが起動しているか確認
3. ファイアウォール設定を確認

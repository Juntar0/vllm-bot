# vLLM Bot - クイックスタート（CLI版）

## 🚀 最速セットアップ

### 1. 依存関係インストール

```bash
cd ~/clawd/vllm-bot
pip install -r requirements.txt
```

### 2. 設定ファイル準備

**CLI専用設定をコピー**:
```bash
cp config/config.cli.json config/config.json
```

**または手動で編集**:
```bash
cp config/config.example.json config/config.json
# config.json を編集
```

### 3. vLLM接続先とモデルを設定

`config/config.json`の`vllm`セクションを編集：

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
  }
}
```

**カスタマイズ例**:

```json
{
  "vllm": {
    "base_url": "http://192.168.1.100:8000/v1",
    "available_models": [
      "llama-3-70b",
      "mixtral-8x7b",
      "qwen-72b"
    ],
    "default_model_index": 0
  }
}
```

- `available_models`: 選択可能なモデルのリスト
- `default_model_index`: デフォルトで選択されるモデル（0始まり）

### 4. ボット起動

```bash
python cli.py
```

### 5. モデル選択

```
Available models:
  1. gpt-oss-low
  2. gpt-oss-medium (default)
  3. gpt-oss-high

Select model (1-3) [default: 2]: 
```

**Enter**キーでデフォルトモデルを選択。

**カスタムモデルを追加した場合**:
```
Available models:
  1. llama-3-70b (default)
  2. mixtral-8x7b
  3. qwen-72b

Select model (1-3) [default: 1]: 
```

### 6. 会話開始！

```
You: こんにちは

Bot: こんにちは！何かお手伝いできることはありますか？
```

---

## 💡 使用例

### ファイル操作

```
You: ワークスペースにREADME.mdを作成して

Bot: TOOL_CALL: {
  "name": "write",
  "args": {
    "path": "README.md",
    "content": "# My Project\n\nWelcome!"
  }
}

Tool execution results:
1. write
Result: Successfully wrote to README.md

Bot: README.mdファイルを作成しました！
```

### コマンド実行

```
You: ファイル一覧を見せて

Bot: TOOL_CALL: {
  "name": "exec",
  "args": { "command": "ls -la" }
}

Tool execution results:
1. exec
Result: total 24
drwxr-xr-x 2 user user 4096 Jan 29 14:00 .
drwxr-xr-x 5 user user 4096 Jan 29 14:00 ..
-rw-r--r-- 1 user user   20 Jan 29 14:00 README.md

Bot: 現在のワークスペースには以下のファイルがあります：
- README.md
```

### ファイル読み取り

```
You: README.mdの内容を教えて

Bot: TOOL_CALL: {
  "name": "read",
  "args": { "path": "README.md" }
}

Tool execution results:
1. read
Result: Read 2 lines (total: 2)
File: README.md

# My Project

Welcome!

Bot: README.mdの内容は以下の通りです：
タイトル: My Project
内容: Welcomeメッセージが記載されています。
```

### 複数ツールの連鎖

```
You: test.txtファイルを作って、その内容を確認して

Bot: TOOL_CALL: {
  "name": "write",
  "args": {
    "path": "test.txt",
    "content": "This is a test file."
  }
}

Tool execution results:
1. write
Result: Successfully wrote to test.txt

(次のイテレーション)

TOOL_CALL: {
  "name": "read",
  "args": { "path": "test.txt" }
}

Tool execution results:
1. read
Result: This is a test file.

Bot: test.txtファイルを作成し、内容を確認しました！
```

---

## 🛠️ コマンド

### /reset

会話履歴をリセット：

```
You: /reset
✅ Conversation history reset!
```

### /help

ヘルプを表示：

```
You: /help

📖 Help:
...
```

### /exit

ボットを終了：

```
You: /exit

👋 Goodbye!
```

**または** `Ctrl+C` で終了。

---

## ⚙️ 設定カスタマイズ

### モデル追加・変更

```json
{
  "vllm": {
    "available_models": [
      "your-model-1",
      "your-model-2",
      "your-model-3"
    ],
    "default_model_index": 0
  }
}
```

**注意**: モデル名はvLLMサーバー側で提供されているものと一致させる必要があります。

### ワークスペース変更

```json
{
  "workspace": {
    "dir": "/path/to/your/workspace"
  }
}
```

### 許可コマンド追加

```json
{
  "security": {
    "allowed_commands": [
      "ls", "cat", "grep", "git", "python", "node"
    ]
  }
}
```

### システムプロンプト変更

```json
{
  "system_prompt": {
    "role": "You are a Python coding assistant."
  }
}
```

---

## 🐛 トラブルシューティング

### vLLM接続エラー

```
Error: vLLM API error: Connection refused
```

**解決策**:
1. vLLMサーバーが起動しているか確認
2. `base_url`が正しいか確認（`http://localhost:8000/v1`）
3. ファイアウォール設定を確認

### モデルが見つからない

```
Error: Model not found: gpt-oss-medium
```

**解決策**:
vLLMサーバー側で該当モデルが設定されているか確認。

### ツールが実行されない

**原因**: モデルがツール呼び出し形式を出力していない

**解決策**:
1. `system_prompt.role`を調整してツール使用を促す
2. 手動でツールを指示：「execツールで`ls`を実行して」

---

## 📊 パフォーマンス

### モデル選択の目安

- **gpt-oss-low**: 遅いが高精度
- **gpt-oss-medium**: バランス型（推奨）
- **gpt-oss-high**: 高速だが精度は低め

### 会話履歴のリセット

長時間使用すると会話履歴が膨大に：

```
You: /reset
```

定期的にリセットすることでレスポンスが改善。

---

## 🎯 次のステップ

1. ✅ CLI版を試す
2. 📝 プロジェクト固有の設定をカスタマイズ
3. 🔧 許可コマンドを調整
4. 🚀 Telegram版も試してみる（`main.py`）

詳細は `README.md` と `DEVELOPMENT.md` を参照！

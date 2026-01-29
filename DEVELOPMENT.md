# vLLM Bot - 開発ドキュメント

**作成日**: 2026-01-29

## プロジェクト背景

Clawdbotのソースコード解析から得た知見を元に、vLLMの`v1/chat/completions` APIのみを使用するシンプルなボットを実装。

## 設計方針

### 1. 最小構成

Clawdbotは43個のコンポーネントを持つ大規模システムだが、このボットは最小限の構成：

- **5つのモジュール** (vllm_provider, tools, agent, telegram_bot, main)
- **1つの設定ファイル** (config.json)
- **1つのワークスペース** (workspace/)

### 2. Clawdbotから学んだこと

#### システムプロンプト
- **動的生成**: ハードコードせず、設定から構築
- **ツール説明**: 利用可能なツールを自動的にプロンプトに含める

#### セキュリティ
- **パス検証**: `_validate_path()`でパストラバーサル防止
- **コマンドallowlist**: `allowed_commands`で実行可能コマンドを制限
- **出力制限**: 最大20万文字、中央切り捨て

#### ツール設計
- **read/write/edit/exec**: Clawdbotと同じインターフェース
- **Claude Code互換**: 将来的に`file_path`→`path`変換を追加可能

#### 会話管理
- **user_id単位**: ユーザーごとに会話履歴を保持
- **システムプロンプト**: 各会話の先頭に追加

### 3. vLLM特化

#### テキストベースのツール呼び出し

vLLMの多くのモデルはfunction callingに対応していないため、テキストパース方式を採用：

```
TOOL_CALL: {
  "name": "read",
  "args": { "path": "file.txt" }
}
```

正規表現でパース：
```python
pattern = r'TOOL_CALL:\s*(\{[^}]+\})'
```

#### Agentic Loop

最大5回のツール実行を許可：

```
User → vLLM → Tool → vLLM → Tool → ... → Final Response
```

## アーキテクチャ詳細

### モジュール構成

```
vllm-bot/
├── main.py                     # エントリーポイント
├── config/
│   └── config.example.json    # 設定テンプレート
└── src/
    ├── vllm_provider.py       # vLLM API呼び出し
    ├── tools.py               # ツール実装
    ├── agent.py               # エージェント（オーケストレーション）
    └── telegram_bot.py        # Telegram統合
```

### データフロー

#### 1. メッセージ受信フロー

```
Telegram Update
      ↓
TelegramBot.handle_message()
      ↓
Agent.chat(user_id, message)
      ↓
[Agentic Loop開始]
      ↓
VLLMProvider.chat_completion(conversation)
      ↓
Agent._parse_tool_calls(response)
      ↓
ToolExecutor.execute(tool_name, args)
      ↓
会話履歴に追加
      ↓
[次のループ or 最終レスポンス]
      ↓
TelegramBot → User
```

#### 2. 会話履歴構造

```python
conversation = [
    {"role": "system", "content": "You are..."},  # システムプロンプト
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! TOOL_CALL: ..."},
    {"role": "user", "content": "Tool execution results: ..."},
    {"role": "assistant", "content": "Based on the results..."}
]
```

### vLLM Provider実装

#### chat_completion()

```python
POST {base_url}/chat/completions
{
  "model": "meta-llama/Llama-2-70b-chat-hf",
  "messages": [...],
  "temperature": 0.7,
  "max_tokens": 2048
}
```

#### ストリーミング対応

```python
if stream:
    for line in response.iter_lines():
        if line.startswith("data: "):
            yield json.loads(line[6:])
```

### ツール実装

#### read

- オフセット・リミット対応
- エラーハンドリング（ファイル未存在等）

#### write

- 親ディレクトリ自動作成
- UTF-8エンコーディング

#### edit

- 完全一致検索
- 1箇所のみ置換（複数マッチは拒否）

#### exec

- タイムアウト（デフォルト30秒）
- 出力制限（20万文字、中央切り捨て）
- allowlistチェック

## セキュリティ設計

### 1. パス検証

```python
def _validate_path(self, path: str) -> Path:
    resolved = (self.workspace_dir / path).resolve()
    try:
        resolved.relative_to(self.workspace_dir)
    except ValueError:
        raise ValueError(f"Path outside workspace: {path}")
    return resolved
```

**防御対象**:
- `../../../etc/passwd`
- `/etc/passwd`
- シンボリックリンク経由の脱出

### 2. コマンドallowlist

```python
if cmd_parts and self.allowed_commands:
    cmd_name = cmd_parts[0]
    if cmd_name not in self.allowed_commands:
        return {"error": f"Command not allowed: {cmd_name}"}
```

**制限レベル**:
- `allowed_commands = []` → すべて拒否
- `allowed_commands = ["ls", "cat"]` → lsとcatのみ許可
- `allowed_commands = None` → すべて許可（非推奨）

### 3. ユーザー制限

```python
if self.allowed_users is None:
    return True  # 制限なし
return user_id in self.allowed_users
```

**推奨設定**:
```json
{
  "telegram": {
    "allowed_users": [123456789]  // 自分のIDのみ
  }
}
```

## 拡張可能性

### 1. 他のチャンネル追加

現在はTelegramのみだが、以下を追加可能：

- Discord (`discord.py`)
- Slack (`slack-sdk`)
- WhatsApp (Baileys)

**必要な変更**:
- 新しい`{channel}_bot.py`を作成
- `Agent`インスタンスを共有
- `main.py`で複数チャンネルを起動

### 2. 他のLLMプロバイダー

vLLMの代わりに以下も使用可能：

- OpenAI (同じAPI形式)
- Anthropic (異なるAPI、要アダプター)
- ローカルLM (llama.cpp等)

**必要な変更**:
- `VLLMProvider`を抽象化
- `BaseProvider`を作成
- プロバイダー切替をconfigで制御

### 3. 永続化

現在は会話履歴がメモリのみ。追加可能：

- SQLite (会話履歴)
- Redis (キャッシュ)
- JSONL (Clawdbot形式)

### 4. Function Calling対応

モデルがfunction callingに対応している場合：

```python
# tools.py
tools = TOOL_DEFINITIONS  # OpenAI形式

# vllm_provider.py
payload["tools"] = tools
tool_calls = self.extract_tool_calls(response)
```

## パフォーマンス最適化

### 1. 会話履歴の切り詰め

現在は無制限に蓄積されるため、長時間使用でメモリ枯渇：

```python
# agent.py
MAX_HISTORY_LENGTH = 50

if len(conversation) > MAX_HISTORY_LENGTH:
    # Keep system prompt + last N messages
    conversation = [conversation[0]] + conversation[-MAX_HISTORY_LENGTH:]
```

### 2. 非同期化

現在は同期的だが、asyncioで並列化可能：

```python
async def chat(self, user_id: int, message: str) -> str:
    # ...
    response = await self.vllm.chat_completion_async(conversation)
```

### 3. キャッシュ

vLLMのprompt cachingを活用：

```python
# システムプロンプトをキャッシュ
cache_control = {"type": "ephemeral"}
```

## テスト

### 単体テスト

```bash
pytest tests/
```

### 統合テスト

```bash
# vLLMサーバー起動
vllm serve meta-llama/Llama-2-7b-chat-hf --port 8000

# ボット起動
python main.py

# Telegramでテスト
```

## デプロイ

### Dockerコンテナ

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### systemdサービス

```ini
[Unit]
Description=vLLM Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/clawd/vllm-bot
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Clawdbotとの比較

| 機能 | Clawdbot | vLLM Bot |
|------|----------|----------|
| **言語** | Node.js | Python |
| **コンポーネント数** | 43 | 5 |
| **設定** | clawdbot.json | config.json |
| **チャンネル** | 7種類 | Telegramのみ |
| **プロバイダー** | 複数 | vLLMのみ |
| **プラグイン** | あり | なし |
| **永続化** | JSONL | メモリのみ |
| **セキュリティ** | 高（sandbox等） | 中（allowlist） |
| **複雑度** | 高 | 低 |
| **学習コスト** | 高 | 低 |

## 今後の改善

### 短期
- [ ] 会話履歴の永続化（SQLite）
- [ ] 会話履歴の切り詰め
- [ ] エラーハンドリング強化

### 中期
- [ ] Discord/Slack対応
- [ ] Function Calling対応
- [ ] 非同期化

### 長期
- [ ] プラグインシステム
- [ ] 複数プロバイダー対応
- [ ] Web UI

## 参考資料

- Clawdbotソースコード解析: `~/clawd/clawdbot-analysis/`
- vLLM公式ドキュメント: https://docs.vllm.ai/
- OpenAI API仕様: https://platform.openai.com/docs/api-reference

# Configuration - config.json

単一の設定ファイル `config.json` ですべてを管理します。

## 設定項目

### vLLM API設定
```json
"vllm": {
  "base_url": "http://localhost:8000/v1",
  "model": "gpt-oss-medium",
  "temperature": 0.0,
  "max_tokens": 2048
}
```

- **base_url**: vLLMサーバーのアドレス
- **model**: 使用するモデル
- **temperature**: 応答の多様性（0=確定的、1=多様）
- **max_tokens**: 最大生成トークン数

### ワークスペース設定
```json
"workspace": {
  "dir": "./workspace"
}
```

- **dir**: ファイル操作の基準ディレクトリ
  - `./workspace` - ワークスペース内のみアクセス
  - `/` - システム全体にアクセス可能（開発用）

### セキュリティ設定
```json
"security": {
  "exec_enabled": true,
  "allowed_commands": ["ls", "cat", "grep", "find", "echo", "wc"],
  "timeout_sec": 30,
  "max_output_size": 200000
}
```

- **exec_enabled**: コマンド実行を許可するか
- **allowed_commands**: 実行許可するコマンドリスト
  - `[]` で空にすると全コマンド実行可能（開発用）
  - 特定コマンドのみ許可推奨（本番用）
- **timeout_sec**: コマンド実行の最大時間
- **max_output_size**: 出力の最大文字数

### メモリ設定
```json
"memory": {
  "path": "./data/memory.json",
  "auto_backup": true
}
```

- **path**: 長期記憶ファイルの場所
- **auto_backup**: 自動バックアップを有効にするか

### 監査ログ設定
```json
"audit": {
  "enabled": true,
  "log_path": "./data/runlog.jsonl"
}
```

- **enabled**: 監査ログを有効にするか
- **log_path**: ログファイルの場所

### エージェント設定
```json
"agent": {
  "max_loops": 5,
  "loop_wait_sec": 0.5
}
```

- **max_loops**: 最大ループ回数（1-5推奨）
- **loop_wait_sec**: ループ間のウェイト時間

---

## よくある設定パターン

### パターン1: 本番環境（セキュア）
```json
{
  "workspace": { "dir": "./workspace" },
  "security": {
    "allowed_commands": ["ls", "cat", "grep", "find"],
    "timeout_sec": 30
  }
}
```

### パターン2: 開発環境（自由）
```json
{
  "workspace": { "dir": "/" },
  "security": {
    "allowed_commands": [],
    "timeout_sec": 60
  }
}
```

### パターン3: バランス型（推奨）
```json
{
  "workspace": { "dir": "/" },
  "security": {
    "allowed_commands": ["ls", "cat", "grep", "find", "wc", "head", "tail"],
    "timeout_sec": 30
  }
}
```

---

## 設定変更方法

### 方法1: ファイルを直接編集
```bash
vi config/config.json
# workspace.dir を変更
python3 cli_integrated.py "command"
```

### 方法2: コマンドラインで確認
```bash
python3 cli_integrated.py "command"
# ロード時に設定が表示される
```

---

## セキュリティガイドライン

| 設定 | セキュリティレベル | 用途 |
|------|------------------|------|
| `workspace: ./workspace` + 限定コマンド | 🟢 高 | 本番環境 |
| `workspace: /` + 限定コマンド | 🟡 中 | 日常利用 |
| `workspace: /` + 全コマンド | 🔴 低 | 開発・テスト |

**推奨**: パターン3（バランス型）を使用し、環境に応じて調整。

# パス制限の設定ガイド

## 概要

デフォルトでは、vLLM Bot はワークスペース内（`./workspace`）のみへのアクセスを許可しています。

このガイドでは、ワークスペース外へのアクセスを許可する3つの方法を説明します。

---

## 方法1: 完全に制限なし（最も開放的）

**設定ファイル**: `config/config.unrestricted.json`

```json
{
  "workspace": {
    "dir": "/"
  },
  "security": {
    "exec_enabled": true,
    "allowed_commands": [],
    "timeout_sec": 30,
    "max_output_size": 200000
  }
}
```

**動作**:
- ✅ 全パスへのアクセス許可（`/etc/passwd` など）
- ✅ すべてのコマンド実行許可
- ⚠️ セキュリティリスク：信頼できる環境でのみ使用

**使用方法**:
```bash
python3 cli_integrated.py "Read /etc/passwd" config/config.unrestricted.json
```

**例**:
```
ユーザ: "Read /etc/passwd"
✅ 結果: ファイル内容を表示

ユーザ: "List all Python files in /usr/lib"
✅ 結果: ファイル一覧を表示
```

---

## 方法2: システムアクセス（推奨・バランス）

**設定ファイル**: `config/config.system-access.json`

```json
{
  "workspace": {
    "dir": "/"
  },
  "security": {
    "allowed_commands": ["ls", "cat", "grep", "find", "wc", "head", "tail", "echo"],
    "timeout_sec": 30,
    "max_output_size": 200000
  }
}
```

**動作**:
- ✅ 全パスへのアクセス許可
- ✅ 安全なコマンドのみ実行許可
- ✅ `rm`, `python`, `bash` などの危険なコマンドはブロック
- ✅ バランスの取れたセキュリティ

**使用方法**:
```bash
python3 cli_integrated.py "Find config files" config/config.system-access.json
```

**許可されるコマンド**:
```
✅ ls -la /etc
✅ cat /etc/hostname
✅ grep "pattern" /var/log/syslog
✅ find /home -name "*.pdf"
✅ wc -l /tmp/data.txt
✅ head -20 /proc/cpuinfo
✅ tail -10 /var/log/auth.log
```

**ブロックされるコマンド**:
```
❌ rm -rf /
❌ python -c "code"
❌ sudo whoami
❌ bash -i
❌ chmod 777 /etc/passwd
```

---

## 方法3: カスタム設定（細かい制御）

独自の設定ファイルを作成して、特定の設定を指定できます。

**例: `/home ディレクトリだけアクセス可能**

```bash
cat > config/config.home-only.json << 'EOF'
{
  "vllm": {...},
  "workspace": {
    "dir": "/home"
  },
  "security": {
    "exec_enabled": true,
    "allowed_commands": ["ls", "cat", "grep", "find"],
    "timeout_sec": 30,
    "max_output_size": 200000
  }
}
EOF
```

**使用方法**:
```bash
python3 cli_integrated.py "List user files" config/config.home-only.json
```

---

## セキュリティレベルの比較

| 設定 | パス制限 | コマンド制限 | セキュリティ | 用途 |
|------|--------|-----------|-----------|------|
| デフォルト | ✅ ワークスペースのみ | ⚠️ allowlist | 🟢 高 | 本番環境 |
| system-access | ❌ 全パス | ✅ allowlist | 🟡 中 | 日常利用 |
| unrestricted | ❌ 全パス | ❌ 制限なし | 🔴 低 | テスト環境 |

---

## デフォルト設定での許可パス

```
✅ workspace/file.txt
✅ workspace/subdir/data.json
✅ data/output.txt

❌ /etc/passwd
❌ ../etc/passwd
❌ /root/secret
```

---

## よくある設定パターン

### パターン1: 開発環境（全アクセス許可）

```bash
cp config/config.unrestricted.json config/config.json
python3 cli_integrated.py "Your request"
```

### パターン2: 本番環境（最小限の制限）

```bash
cp config/config.system-access.json config/config.json
python3 cli_integrated.py "Your request"
```

### パターン3: セキュアな本番環境（厳格）

```bash
cp config/config.full.json config/config.json
python3 cli_integrated.py "Your request"
```

---

## コマンドラインでの即時変更

Python API を使用して、実行時にパス制限を変更することも可能です：

```python
from src.agent import Agent
import json

# デフォルト設定を読み込み
config = json.load(open('config/config.full.json'))

# パス制限を緩和
config['workspace']['dir'] = '/'  # ルートディレクトリ許可
config['security']['allowed_commands'] = []  # すべてのコマンド許可

# エージェント実行
agent = Agent(config)
response = agent.run("Read /etc/passwd")
print(response)
```

---

## セキュリティに関する注意

⚠️ **重要**:

1. **パス制限なし（`/`）に設定する場合**
   - 信頼できる環境でのみ使用
   - テスト・開発環境での使用に限定
   - 本番環境では使用しないこと

2. **コマンド制限なし（`[]`）に設定する場合**
   - `rm -rf /` などの危険なコマンド実行可能
   - LLMの出力を完全に信頼できる場合のみ
   - 必ず監視ログを記録（audit）

3. **推奨設定**
   ```json
   {
     "workspace": { "dir": "/" },
     "security": {
       "allowed_commands": ["ls", "cat", "grep", "find", "wc"],
       "timeout_sec": 30
     }
   }
   ```

---

## トラブルシューティング

### Q1: `/etc/passwd` へのアクセスがブロックされる

```
❌ エラー: Path outside allowed root: /etc/passwd
```

**対策**: `config.unrestricted.json` または `config.system-access.json` を使用

### Q2: `python` コマンドが実行されない

```
❌ エラー: Command not allowed: python
```

**対策**: `allowed_commands` に `"python"` を追加（ただし非常に危険）

### Q3: 特定のディレクトリだけアクセスしたい

**対策**: `workspace.dir` をそのディレクトリに設定

```json
{
  "workspace": {
    "dir": "/home/user/projects"
  }
}
```

---

## 推奨される運用方針

| 環境 | 設定 | 説明 |
|------|------|------|
| ローカル開発 | `config.unrestricted.json` | 全パス・全コマンド許可 |
| チーム開発 | `config.system-access.json` | システムアクセス＋コマンド制限 |
| ステージング | `config.full.json` + 監視 | ワークスペースのみ＋監視ログ |
| 本番環境 | `config.full.json` + 厳格ログ | 最大制限＋完全監視 |

---

## まとめ

パス制限の設定レベル：

```
🔴 最も危険
├─ config.unrestricted.json（全アクセス許可）
├─ config.system-access.json（パス許可・コマンド制限）
└─ config.full.json（ワークスペースのみ）
🟢 最も安全
```

**デフォルトの `config.full.json` はセキュリティベストプラクティスに基づいています。**

パス制限を緩和する場合は、環境とセキュリティリスクを十分に検討してください。

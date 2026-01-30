# Setup Wizard Guide

## セットアップ

```bash
rm -f config/config.json  # 既存設定をリセット
./setup.sh
```

## セキュリティレベルの選択

### 1) Restricted（推奨・デフォルト）

```
Security Configuration:
  Command permission level:
    1) Restricted (default: ls, cat, grep, find, echo, wc)
  Choose [1]: 1
```

**結果**: 基本的なコマンドのみ許可

```json
"allowed_commands": ["ls", "cat", "grep", "find", "echo", "wc"]
```

---

### 2) Full Access（全コマンド許可）

```
Security Configuration:
  Command permission level:
    2) Full access (all commands)
  Choose [1]: 2
  Include sudo? (y/n) [n]: y  ← ここで sudo 許可
```

**結果**: すべてのコマンド + sudo 許可

```json
"allowed_commands": ["sudo"]
```

⚠️ **注意**: `allowed_commands` が `[]` の場合 = 全コマンド許可
⚠️ **注意**: `["sudo"]` の場合 = sudo コマンドのみ

---

### 3) Custom（カスタム選択）

```
Security Configuration:
  Command permission level:
    3) Custom (specify commands)
  Choose [1]: 3
  Allowed commands (comma-separated): python,bash,npm
```

**結果**: 指定したコマンドのみ許可

```json
"allowed_commands": ["python", "bash", "npm"]
```

---

## ワークスペース制限

### 1) Restricted（推奨・デフォルト）

```
Workspace Restriction:
  1) Restricted (./workspace only)
  Choose [1]: 1
```

**結果**: `./workspace` ディレクトリのみアクセス可能

---

### 2) Full System Access

```
Workspace Restriction:
  2) Full system access (/)
  Choose [1]: 2
```

**結果**: システム全体にアクセス可能

⚠️ **警告**: 危険な設定です

---

## よくある設定パターン

### パターン1: 安全（デフォルト）

```
Base URL: (Enter)
Model: (Enter)
Workspace: (Enter)
Security: 1
Workspace: 1
Debug: (Enter)
```

**結果**:
- 制限されたコマンドのみ
- ワークスペース内のみアクセス

### パターン2: 開発用（全許可）

```
Base URL: (Enter)
Model: (Enter)
Workspace: (Enter)
Security: 2
Include sudo: y
Workspace: 2
Debug: y
```

**結果**:
- すべてのコマンド + sudo
- システム全体アクセス
- デバッグ有効

### パターン3: カスタム

```
Security: 3
Allowed commands: ls,cat,python,bash
```

**結果**:
- 指定したコマンドのみ

---

## 設定ファイルの確認

```bash
cat config/config.json | python3 -m json.tool
```

設定値:
```json
{
  "security": {
    "allowed_commands": ["ls", "cat", ...],
    "timeout_sec": 30,
    "max_output_size": 200000
  }
}
```

---

## 設定の変更

### 方法1: ウィザード再実行

```bash
rm config/config.json
./setup.sh
```

### 方法2: ファイル直接編集

```bash
vi config/config.json
```

例えば、`allowed_commands` を変更：
```json
"allowed_commands": ["sudo", "ls", "cat", "python"]
```

---

## sudo が必要な理由

**ユースケース**:
```
> Install package with apt
エージェント: sudo apt update && sudo apt install python3-numpy

> Restart service
エージェント: sudo systemctl restart nginx

> Change file permissions
エージェント: sudo chmod 755 script.sh
```

`allowed_commands` に `"sudo"` を追加することで、これらのコマンドが実行可能になります。

---

## セキュリティ推奨事項

### 本番環境（推奨）
```json
"allowed_commands": ["ls", "cat", "grep", "find"],
"workspace": "./workspace"
```

### 開発環境
```json
"allowed_commands": ["sudo"],
"workspace": "/"
```

### テスト環境
```json
"allowed_commands": ["python", "bash", "git"],
"workspace": "/"
```

---

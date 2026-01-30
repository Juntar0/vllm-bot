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
```

**結果**: すべてのコマンド（apt, sudo, pip など全て）が実行可能

```json
"allowed_commands": []
```

✅ **説明**: `"allowed_commands": []` = すべてのコマンド許可（最も自由度が高い）
✅ **含まれるもの**: sudo, apt, apt-get, pip, npm, python, bash など全て

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
Workspace: 2
Debug: y
```

**結果**:
- すべてのコマンド実行可能（apt, sudo, pip, npm など）
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

### allowed_commands の意味

**`[] （空配列）**:
```json
"allowed_commands": []
```
すべてのコマンド実行可能（Full access）

**制限リスト**:
```json
"allowed_commands": ["ls", "cat", "grep", "find"]
```
指定したコマンドのみ実行可能

その他設定:
```json
{
  "security": {
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

**全コマンド許可**:
```json
"allowed_commands": []
```

**特定コマンドのみ許可**:
```json
"allowed_commands": ["sudo", "apt", "apt-get", "ls", "cat", "python"]
```

---

## 全コマンド許可（Full Access）が必要な場合

**ユースケース**:
```
> Package install
エージェント: apt update && apt install python3-numpy

> Service restart
エージェント: systemctl restart nginx

> Permission change
エージェント: chmod 755 script.sh

> System update
エージェント: apt upgrade
```

これらを実行するには、`"allowed_commands": []` に設定して全コマンド許可を有効化します。

**セットアップウィザードで**:
```
Security: 2 (Full access)
```

**または config.json で**:
```json
"allowed_commands": []
```

---

## セキュリティ推奨事項

### 本番環境（推奨・最も制限）
```json
"allowed_commands": ["ls", "cat", "grep", "find"],
"workspace": "./workspace"
```

### 開発環境（全コマンド許可）
```json
"allowed_commands": [],
"workspace": "/"
```

### テスト環境（中程度の制限）
```json
"allowed_commands": ["python", "bash", "git", "npm", "pip"],
"workspace": "/"
```

### allowed_commands の値の意味

| 設定値 | 意味 | 実行可能なコマンド |
|-------|------|------------------|
| `[]` | 全コマンド許可 | apt, sudo, python, npm など全て |
| `["apt", "sudo"]` | 指定のみ許可 | apt と sudo のみ |
| `["ls", "cat"]` | 安全なコマンドのみ | 読み込み操作のみ |

---

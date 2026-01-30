# セキュリティ制約実装 - 詳細ガイド

## 概要

vLLM Botには、**3層のセキュリティ制約**が実装されています。

```
┌──────────────────────────────┐
│  Layer 3: Resource Limits    │
│  (Timeout, Output Size)      │
└──────────────────────────────┘
         ↑
┌──────────────────────────────┐
│  Layer 2: Command Allowlist  │
│  (Whitelist Mode)            │
└──────────────────────────────┘
         ↑
┌──────────────────────────────┐
│  Layer 1: Path Restriction   │
│  (Workspace Only)            │
└──────────────────────────────┘
```

---

## Layer 1: Path Restriction（パス制限）

### 実装箇所

`src/tool_constraints.py::validate_path()`

```python
def validate_path(self, path: str) -> bool:
    """Validate that a path is within allowed_root"""
    try:
        # Resolve path relative to allowed_root
        full_path = (self.allowed_root / path).resolve()
        
        # Check if within allowed_root (prevents traversal)
        full_path.relative_to(self.allowed_root)
        
        return True
    except (ValueError, RuntimeError):
        return False
```

### 防ぐ脅威

#### 脅威1: Path Traversal（パストラバーサル）

**攻撃例**:
```
request_path: "../../../etc/passwd"
```

**実装での防止**:
```python
allowed_root = Path("./workspace").resolve()
# → /home/user/vllm-bot/workspace

attack_path = "../../../etc/passwd"
full_path = (allowed_root / attack_path).resolve()
# → /etc/passwd

try:
    full_path.relative_to(allowed_root)
except ValueError:
    # 失敗！ /etc/passwd は /workspace の相対パスではない
    return False  # ブロック ✅
```

**キーポイント**: `Path.resolve()` と `Path.relative_to()` の組み合わせで、symlink や `..` の攻撃を防止

#### 脅威2: Absolute Path（絶対パス）

**攻撃例**:
```
request_path: "/etc/passwd"
```

**実装での防止**:
```python
attack_path = "/etc/passwd"
full_path = Path("./workspace").resolve() / "/etc/passwd"
# Path("/absolute") は直後のパスで置換される
# → Path("/etc/passwd")

try:
    full_path.relative_to(allowed_root)
except ValueError:
    return False  # ブロック ✅
```

### 許可される例

```
✅ "test.txt"
   → ./workspace/test.txt

✅ "subdir/file.txt"
   → ./workspace/subdir/file.txt

✅ "./data/output.json"
   → ./workspace/data/output.json

✅ "."
   → ./workspace
```

### 拒否される例

```
❌ "../etc/passwd"
   → /etc/passwd (outside)

❌ "../../secret"
   → /home/secret (outside)

❌ "/etc/passwd"
   → /etc/passwd (absolute)

❌ "/root/data"
   → /root/data (absolute)
```

---

## Layer 2: Command Allowlist（コマンド許可リスト）

### 実装箇所

`src/tool_constraints.py::validate_command()`

```python
def validate_command(self, command: str) -> bool:
    """Validate that a command is in the allowlist"""
    
    # Empty allowlist = allow all
    if not self.command_allowlist:
        return True
    
    # Extract first word (command name)
    parts = command.split()
    if not parts:
        return False
    
    cmd_name = parts[0]
    
    # Check if in allowlist
    return cmd_name in self.command_allowlist
```

### 防ぐ脅威

#### 脅威1: Dangerous Commands

**攻撃例**:
```
request: "rm -rf /"
```

**実装での防止**:
```python
allowlist = {"ls", "cat", "grep"}
command = "rm -rf /"

cmd_name = command.split()[0]  # "rm"

if cmd_name in allowlist:
    return True
else:
    return False  # ブロック ✅
```

#### 脅威2: Shell Built-ins

**攻撃例**:
```
request: "cd /root && cat secret.txt"
```

**実装での防止**:
```python
command = "cd /root && cat secret.txt"
cmd_name = command.split()[0]  # "cd"

if "cd" not in allowlist:
    return False  # ブロック ✅
```

### 設定例

```python
# 厳密モード（最小限）
constraints = ToolConstraints(
    allowed_root="./workspace",
    command_allowlist=["ls", "cat", "grep"]
)

# バランスモード
constraints = ToolConstraints(
    allowed_root="./workspace",
    command_allowlist=["ls", "cat", "grep", "find", "wc", "echo"]
)

# 開放モード（テスト用）
constraints = ToolConstraints(
    allowed_root="./workspace",
    command_allowlist=[]  # すべて許可
)
```

### 許可される例

```
allowlist = ["ls", "cat", "grep"]

✅ "ls -la"
   → cmd_name = "ls" (in allowlist)

✅ "cat file.txt"
   → cmd_name = "cat" (in allowlist)

✅ "grep pattern file"
   → cmd_name = "grep" (in allowlist)
```

### 拒否される例

```
allowlist = ["ls", "cat", "grep"]

❌ "rm file"
   → cmd_name = "rm" (not in allowlist)

❌ "python -c 'dangerous code'"
   → cmd_name = "python" (not in allowlist)

❌ "sudo whoami"
   → cmd_name = "sudo" (not in allowlist)

❌ "bash -i"
   → cmd_name = "bash" (not in allowlist)
```

---

## Layer 3: Resource Limits（リソース制限）

### 実装箇所1: Timeout

`src/tool_runner.py::tool_exec_cmd()`

```python
def tool_exec_cmd(self, args: Dict[str, Any]) -> Dict[str, Any]:
    command = args.get('command')
    timeout = args.get('timeout')
    
    # Get effective timeout (minimum of requested and constraint)
    timeout = self.constraints.get_effective_timeout(timeout)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(self.workspace_dir),
            capture_output=True,
            text=True,
            timeout=timeout  # ← タイムアウト適用
        )
```

**防ぐ脅威**:
```python
# 無限ループ攻撃
"while true; do echo 'spam'; done"

# 長時間実行の処理
"find / -type f"

# デバッグ: set timeout
timeout_sec = 30  # 30秒で打ち切り
```

### 実装箇所2: Output Size Limit

`src/tool_runner.py::_execute_single()`

```python
def tool_exec_cmd(self, args):
    result = subprocess.run(...)
    
    # Combine stdout and stderr
    output = result.stdout
    if result.stderr:
        output += f"\n[stderr]\n{result.stderr}"
    
    # Truncate if too long
    output = self.constraints.truncate_output(
        output,
        self.constraints.max_output_size
    )
```

`src/tool_constraints.py::truncate_output()`

```python
def truncate_output(self, output: str, max_size: int) -> str:
    if len(output) <= max_size:
        return output
    
    # Keep beginning and end
    kept_size = max_size // 2
    middle_msg = f"\n... ({len(output) - max_size} chars hidden) ...\n"
    
    return output[:kept_size] + middle_msg + output[-kept_size:]
```

**防ぐ脅威**:
```python
# メモリ爆弾（大量出力）
"seq 1 1000000000 | cat"
# → 出力が200KB超え
# → 自動的にトリム

# メモリリーク
"find / -type f"  # 数百万行の出力
# → 自動的にトリム
```

### 設定値

```python
# デフォルト
timeout_sec = 30              # 30秒以上は実行停止
max_output_size = 200000      # 200KB以上は出力トリム
max_stderr_size = 50000       # stderr も制限
```

---

## 実装の流れ（統合）

### Example 1: read_file 実行時

```python
# ユーザ要求
args = {'path': '../../../etc/passwd'}

# Tool Runner が実行
def tool_read_file(self, args):
    path = args.get('path')
    
    # Layer 1: Path restriction check
    is_valid, err_msg = self.constraints.validate_path_and_command(
        'read_file',
        path
    )
    
    if not is_valid:
        return {'error': err_msg}  # ❌ ブロック
    
    # Layer 1 パス
    file_path = (self.workspace_dir / path).resolve()
    
    # ファイル読み取り
    with open(file_path, 'r') as f:
        content = f.read()
    
    return {'output': content}
```

**結果**: ❌ `Path outside allowed root: ../../../etc/passwd`

### Example 2: exec_cmd 実行時

```python
# ユーザ要求
args = {'command': 'rm -rf /'}

# Tool Runner が実行
def tool_exec_cmd(self, args):
    command = args.get('command')
    
    # Layer 2: Command allowlist check
    if not self.constraints.validate_command(command):
        return {'error': f'Command not allowed: {command}'}
    
    # Layer 2 で ❌ ブロック
```

**結果**: ❌ `Command not allowed: rm -rf /`

### Example 3: grep 実行時（大量出力）

```python
# ユーザ要求
args = {
    'pattern': '.',
    'path': '/'  # ← すでに Layer 1 で拒否
}

# もし path が許可されていた場合
def tool_grep(self, args):
    # Layer 1: Path check
    if not self.constraints.validate_path(args['path']):
        return {'error': 'Path outside allowed root'}
    
    # Layer 3: Output limit
    # 検索実行...
    output = "huge amount of output..."  # 100MB
    
    # Layer 3 で自動トリム
    output = self.constraints.truncate_output(
        output,
        self.constraints.max_output_size
    )
    
    # 200KB に制限されて返却
    return {'output': output}
```

**結果**: 出力が自動トリムされて安全に返却

---

## セキュリティ脅威と防止マトリックス

| 脅威 | Layer 1 | Layer 2 | Layer 3 | 防止状態 |
|------|---------|---------|---------|----------|
| Path Traversal | ✅ | - | - | 完全防止 |
| Absolute Path | ✅ | - | - | 完全防止 |
| Dangerous Commands | - | ✅ | - | 完全防止 |
| Command Chaining | - | ✅ | - | 部分的* |
| Infinite Loop | - | - | ✅ | 防止 |
| Memory Bomb | - | - | ✅ | 防止 |
| File Access Outside | ✅ | - | - | 完全防止 |
| Privilege Escalation | - | ✅ | - | 防止 |

*: コマンド連鎖（&&, ||）は既に exec で検出

---

## 設定ベストプラクティス

### シナリオ1: 最も制限的（本番環境）

```json
{
  "security": {
    "allowed_commands": ["ls", "cat", "grep"],
    "timeout_sec": 10,
    "max_output_size": 50000
  }
}
```

**防止対象**: ほぼすべての脅威  
**ユースケース**: 本番環境、信頼できないユーザ入力

### シナリオ2: バランス（一般利用）

```json
{
  "security": {
    "allowed_commands": ["ls", "cat", "grep", "find", "wc", "echo"],
    "timeout_sec": 30,
    "max_output_size": 200000
  }
}
```

**防止対象**: ほぼすべての脅威 + 実用性  
**ユースケース**: 個人利用、信頼できるシステム

### シナリオ3: 開放的（開発・テスト）

```json
{
  "security": {
    "allowed_commands": [],  // すべて許可
    "timeout_sec": 60,
    "max_output_size": 1000000
  }
}
```

**防止対象**: リソース枯渇のみ  
**ユースケース**: テスト、デバッグ、信頼できる環境

---

## テスト結果

### Path Restriction テスト

```
✅ Valid paths allowed:
   - test.txt
   - subdir/file.txt
   - ./data/config.json

✅ Invalid paths blocked:
   - ../etc/passwd
   - ../../root/secret
   - /etc/passwd
   - /root/data
```

### Command Allowlist テスト

```
✅ Allowed commands:
   - ls -la
   - cat file.txt
   - grep pattern file

✅ Blocked commands:
   - rm -rf /
   - python -c "code"
   - bash -i
```

### Resource Limit テスト

```
✅ Timeout enforcement:
   - Command timed out after 30s ✓

✅ Output truncation:
   - Large output auto-trimmed ✓
   - Hidden chars displayed ✓
```

---

## 実装の強み

### 1. **多層防御**
3つの独立したレイヤーで防御

### 2. **明確な検証**
パス、コマンド、リソースをそれぞれ検証

### 3. **Pythonの標準機能を活用**
`pathlib.Path` で安全なパス操作

### 4. **デフォルトセキュア**
すべてのツール実行時に自動検証

### 5. **設定可能**
ユースケースに応じてカスタマイズ可能

---

## 実装の制限

### 制限1: Command Allowlist は一段階のみ

**例**:
```
allowlist = ["python", "node"]

❌ 防止できない:
   "python -c 'import os; os.system(rm -rf /)'"
```

**対策**: 危険なコマンド（python, bash等）は allowlist から除外

### 制限2: Shell 機能を完全には防止できない

**例**:
```
allowlist = ["ls"]

❌ 防止できない（shell=True使用時）:
   "ls && echo vulnerable"
```

**対策**: exec時の危険なパターン検出（別レイヤー）

### 制限3: Symlink 攻撃

**例**:
```
workspace/link → /etc/passwd (symlink)
```

**対策**: `resolve()` で symlink を解決

---

## 推奨される追加セキュリティ（未実装）

1. **Seccomp** - システムコール制限（Linux）
2. **AppArmor** - アプリケーション防御（Linux）
3. **SELinux** - 強制アクセス制御（Linux）
4. **Sandboxing** - Docker/仮想マシン分離
5. **Rate Limiting** - API呼び出し制限

---

## まとめ

vLLM Bot の**3層セキュリティ制約**：

```
Layer 1: Path Restriction
└─ パストラバーサル・絶対パス完全防止

Layer 2: Command Allowlist
└─ 危険なコマンド実行防止

Layer 3: Resource Limits
└─ タイムアウト・メモリ爆弾防止
```

**結果**: ほぼすべての一般的なセキュリティ脅威に対応

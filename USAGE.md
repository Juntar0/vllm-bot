# ユーザインタラクション - USAGE.md

## 対話型インタフェース（実装済み）

複数の質問を順番に処理できます。

### 基本的な使用方法

```bash
$ python3 cli.py

> Find Python files
Found 42 Python files

> Count total lines
15,420 lines of code

> List files by size
Top 5 largest:
1. main.py: 2,340 lines
2. utils.py: 1,560 lines
3. config.py: 1,245 lines
...

> exit
Goodbye! 👋
```

---

## 会話フロー

### ユーザの視点

```
ユーザ入力
  ↓
エージェント処理
  ↓
エージェント出力
  ↓
ユーザ入力（次の質問）
  ↓
...
```

### エージェント内での自動処理

ユーザが見えないところで、複数ループで自動的に処理：

```
Loop 1:
  🧠 Planner: "ファイルを見つける必要がある"
  🔨 Tools: find *.py → [ファイルリスト]
  💬 Responder: "42 個のファイルが見つかりました"

Loop 2（同じリクエスト内）:
  🧠 Planner: "タスク完了、ツール不要"
  🔨 Tools: (なし)
  💬 Responder: "最終回答の準備完了"
  ⛔ STOP
```

---

## 対話型のメリット

### ✅ シンプル

```bash
python3 cli.py
> 質問
エージェントの回答
> 次の質問
エージェントの回答
```

### ✅ 自然な会話

```
> Analyze these files
Analysis: 42 files found

> Compare with yesterday
Comparison data: ...

> Generate report
Report generated
```

### ✅ コンテキスト保持

```
> Find large files
Found 5 files > 1000 lines

> Which one is main.py?
main.py: 2,340 lines (largest)

> Show its content
[file content displayed]
```

前の質問の回答が context として使用されます。

### ✅ 対話中のコマンド

```
> help                    # ヘルプ表示
> clear                   # 会話クリア（新規開始）
> debug on/off            # デバッグ切り替え
> config                  # 設定表示
> exit / quit             # 終了
```

---

## 使用シーン別ガイド

### シーン1: ファイル操作タスク

```
> List all config files
Found: config.json, app.conf, settings.yaml

> What's the size of config.json?
12.5 KB

> Show first 10 lines
[content shown]

> Find similar files
Found 3 config files
```

### シーン2: ログ分析

```
> Find error logs from today
Found 3 files with errors

> Count total errors
1,245 errors

> What are the top error types?
- ConnectionError: 432
- TimeoutError: 356
- ParsingError: 457

> Show errors from last hour
42 errors in the last hour
```

### シーン3: コード分析

```
> Analyze code quality
42 Python files
15,420 total lines

> Find files with high complexity
5 files with high complexity

> What's the largest function?
calculate_metrics() in main.py: 340 lines

> Suggest refactoring
Recommended: Split into 3 smaller functions
```

---

## デバッグ付き対話

```bash
$ python3 cli.py

> debug on
✓ Debug enabled

> Find Python files
[DEBUG PLANNER] Need tools: true
[DEBUG PLANNER] Tool calls: 1
[DEBUG PLANNER]   - find(pattern: *.py)
[DEBUG TOOL_RUNNER] Executing: find
[DEBUG TOOL_RUNNER] ✓ find completed (42 files)
[DEBUG RESPONDER] Is final answer: true
[DEBUG RESPONDER] Response: Found 42 files
Found 42 Python files

> Count lines
[DEBUG PLANNER] Need tools: true
[DEBUG PLANNER] Tool calls: 1
[DEBUG PLANNER]   - exec_cmd(wc -l)
[DEBUG TOOL_RUNNER] Executing: exec_cmd
[DEBUG TOOL_RUNNER] ✓ exec_cmd completed (2048 chars)
[DEBUG RESPONDER] Response: 15,420 lines
15,420 lines

> debug off
✓ Debug disabled
```

---

## メモリの活用

エージェントは **長期記憶** を持つため、複数回の対話から学習します：

```
Turn 1:
> Preferred output format?
> Recommended: JSON format

Turn 2:
> Analyze files
[JSON format で出力]

Turn 3:
> Compare results
[JSON format で出力]
# メモリから "JSON形式が好き" を学習
```

---

## 会話のリセット

新しい話題に移る場合：

```
> clear
✓ Conversation cleared

> Start new task
[新しい context で開始]
```

---

## 設定の変更

実行中に設定を変更：

```
> debug on            # デバッグ有効
✓ Debug enabled

> debug off           # デバッグ無効
✓ Debug disabled

> config              # 現在の設定表示
Current Configuration:
  Model: gpt-oss-medium
  Workspace: ./workspace
  Max loops: 5
  Debug: false
```

---

## よくある質問

### Q1: 複数ループって何？

A: エージェントが内部で複数回のプランニング→ツール実行→回答を繰り返すこと。最大 5 回まで。

```
Loop 1: ファイル一覧取得
Loop 2: ファイルサイズ計算
Loop 3: 統計情報集計
Loop 4: タスク完了確認
STOP
```

ユーザは 1 回の質問で、複数のステップが自動的に処理されます。

### Q2: メモリは何を覚えているの？

A: 過去の回答から学習します：
- ユーザの好みの形式（JSON、テーブル、リスト等）
- よく使うコマンド
- 設定の好み

### Q3: 会話履歴は保存される？

A: 実行中のみ保持されます。`exit` で終了すると、次回の起動は新規開始です。

永続的に保存したい場合は、設定ファイルを編集：

```json
{
  "memory": {
    "path": "./data/memory.json",
    "auto_backup": true
  }
}
```

### Q4: 何回まで質問できる？

A: 無制限です。ただし、`clear` でリセットされるまで、会話履歴が蓄積されます。

---

## ベストプラクティス

### ✅ 効果的な質問

```
> Find error logs and count them
✓ 複合的なリクエスト OK

> Show errors by type with percentages
✓ 詳細な要求 OK
```

### ✅ デバッグの活用

```
> debug on
> [動作が変な時]
> debug off
✓ 問題解決に役立つ
```

### ✅ 会話のリセット

```
> clear
✓ 新しい話題に移る時は clear を実行
```

---

## 推奨される使用方法

1. **対話型で開始**
   ```bash
   python3 cli.py
   ```

2. **複数の関連質問をする**
   ```
   > Find files
   > Analyze
   > Generate report
   ```

3. **デバッグが必要な場合**
   ```
   > debug on
   > [調査]
   > debug off
   ```

4. **終了**
   ```
   > exit
   ```

---

## まとめ

| 特徴 | 説明 |
|------|------|
| **対話型** | > プロンプトで複数質問可 |
| **自動処理** | 複数ループで自動的に処理 |
| **メモリ** | 前の回答をコンテキストに使用 |
| **デバッグ** | 内部処理を可視化可能 |
| **コマンド** | help/clear/debug/config/exit |

**対話型インタフェースで、効率的に作業できます！** 🎯

# Logging Guide

## ログの自動記録

vLLM Bot は実行時に自動的にすべてのアクティビティを **./data/debug.log** に記録します。

### ログファイルに記録される内容

✅ 実行されたすべてのコマンド
✅ コマンドの完全な出力（省略なし）
✅ エラーメッセージと終了コード
✅ vLLM API リクエスト・レスポンス
✅ Planner・Responder の決定
✅ Tool 実行の詳細結果
✅ 各イベントのタイムスタンプ

### ログファイルを確認

```bash
# 最新のログを見る
tail -f data/debug.log

# grep で特定のコマンドを検索
grep "apt update" data/debug.log

# エラーだけを抽出
grep -i error data/debug.log

# Tool execution の詳細を見る
grep -A 20 "exec_cmd Full Result" data/debug.log
```

---

## コンソール出力 vs ログファイル

### コンソール出力（verbose debug mode 有効時）

```
> apt updateしてみてください

[DEBUG PLANNER] Reason: Execute apt update...
[DEBUG TOOL_RUNNER] ✓ exec_cmd completed (445 chars)
[DEBUG RESPONDER] Is final answer: True
Response: apt update が実行されましたが...
```

**特徴**:
- コンパクトで読みやすい
- 重要な情報のみ表示
- インタラクティブな使用に最適

### ログファイル出力（常に記録）

```
[2026-01-30T11:00:45.123456] [PLANNER] Reason: Execute apt update to fulfill...

[2026-01-30T11:00:45.234567] [TOOL_RUNNER] --- exec_cmd Full Result ---
  FULL_DETAIL:
    {
      "success": false,
      "output": "Reading package lists...
E: Could not open lock file /var/lib/apt/lists/lock - open (13: Permission denied)
E: Unable to lock directory /var/lib/apt/lists/
W: Problem unlinking the file /var/cache/apt/pkgcache.bin - RemoveCaches (13: Permission denied)
W: Problem unlinking the file /var/cache/apt/srcpkgcache.bin - RemoveCaches (13: Permission denied)",
      "error": "",
      "exit_code": 100,
      "duration_sec": 0.0285,
      "output_length": 445
    }

[2026-01-30T11:00:46.345678] [RESPONDER] --- Input to Responder ---
[2026-01-30T11:00:46.345678] Original request: apt updateしてみてください
```

**特徴**:
- 完全な詳細情報
- タイムスタンプ付き
- デバッグと監査に最適
- 省略なし

---

## ログの設定

### デフォルト設定

```json
{
  "debug": {
    "enabled": false,
    "level": "basic",
    "log_file": "./data/debug.log"
  }
}
```

これでもログは記録されます（コンソール出力なし）。

### コンソール出力＋ログ記録

ログファイルにも記録しつつ、コンソール出力も見たい場合：

```json
{
  "debug": {
    "enabled": true,
    "level": "verbose",
    "log_file": "./data/debug.log"
  }
}
```

### ログをファイルに記録しない

```json
{
  "debug": {
    "enabled": false,
    "level": "basic",
    "log_file": null
  }
}
```

---

## 実行結果を確認する流れ

### 1. コマンド実行

```bash
./run.sh

> apt updateしてみてください
```

### 2. コンソール出力を確認

```
apt update が実行されましたが、ロックファイル...
```

### 3. 詳細をログファイルで確認

```bash
tail -100 data/debug.log
```

### 4. 特定の情報を検索

```bash
# apt コマンドの詳細結果
grep -B 5 -A 50 "apt.*Full Result" data/debug.log

# 権限エラーの詳細
grep -B 10 "Permission denied" data/debug.log

# 実行時間
grep "duration_sec" data/debug.log
```

---

## ログファイルの構造

```
[timestamp] [section] message
  FULL_DETAIL:
    (JSON or detail content)

```

### セクション名

| セクション | 内容 |
|-----------|------|
| AGENT | メインエージェント |
| AGENT_LOOP | ループ制御 |
| PLANNER | 計画エージェント |
| TOOL_RUNNER | ツール実行 |
| RESPONDER | 応答生成 |
| VLLM_API | vLLM API |
| EXECUTION | 実行結果 |

### 例

```
[2026-01-30T11:00:45.123456] [TOOL_RUNNER] Executing: exec_cmd
[2026-01-30T11:00:45.234567] [TOOL_RUNNER] --- exec_cmd Full Result ---
  FULL_DETAIL:
    {
      "success": false,
      "output": "...",
      "error": "",
      "exit_code": 100,
      "duration_sec": 0.0285
    }
```

---

## トラブルシューティングにログを活用

### 問題: コマンド実行に失敗した

```bash
grep -A 20 "exec_cmd Full Result" data/debug.log | head -30
```

出力で確認：
- success: true/false
- exit_code: 終了コード
- output: 完全な出力
- error: エラーメッセージ

### 問題: vLLM API が失敗

```bash
grep -B 5 -A 20 "VLLM_API.*Error" data/debug.log
```

### 問題: Planner が適切に判断していない

```bash
grep -A 30 "PLANNER.*API Request" data/debug.log | head -40
```

投げたプロンプト全体が見えます。

### 問題: 実行が遅い

```bash
grep "duration_sec" data/debug.log
```

各ツール実行の時間を確認。

---

## ログローテーション

ログファイルが大きくなった場合：

```bash
# バックアップを作成
cp data/debug.log data/debug.log.bak

# 新しいログを開始
rm data/debug.log

# または
mv data/debug.log "data/debug.log.$(date +%Y%m%d-%H%M%S)"
```

次回実行時に新しいファイルが作成されます。

---

## ログの活用例

### 実行履歴を確認

```bash
grep "User input:" data/debug.log
```

### すべてのエラーを見る

```bash
grep -i "error\|failed\|denied" data/debug.log
```

### API の往復を追跡

```bash
grep "VLLM_API" data/debug.log | grep -E "Request|Response"
```

### ツール実行の成功率

```bash
grep '"success": true' data/debug.log | wc -l
grep '"success": false' data/debug.log | wc -l
```

---

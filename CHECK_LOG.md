# ログファイルの完全性を確認

## ログファイルの保存場所

```bash
cat data/debug.log
```

## 最後の Tool 実行結果を確認

```bash
# 最後の tool_result_detail を見る
tail -200 data/debug.log | grep -A 50 "Full Result"
```

## 特定のコマンドの完全な結果を確認

```bash
# apt update の結果全体を見る
grep -A 100 "exec_cmd Full Result" data/debug.log | tail -80
```

## ログファイルのサイズを確認

```bash
wc -l data/debug.log       # 行数
du -h data/debug.log       # ファイルサイズ
```

## JSON の完全性を確認

```bash
# JSON の最後が } で閉じているか確認
tail -50 data/debug.log | grep -E '^\s*}'

# JSON の括弧のバランスを確認
grep -o '{' data/debug.log | wc -l  # { の数
grep -o '}' data/debug.log | wc -l  # } の数
# 同じ数なら OK
```

## apt update の完全な出力を抽出

```bash
# exec_cmd の結果から "output" フィールドを抽出
grep -A 50 '"output":' data/debug.log | head -30

# または awk で JSON から output の値を抽出
awk '/exec_cmd Full Result/,/^$/' data/debug.log
```

## ファイルの最後部分を確認

```bash
# 最後 50 行
tail -50 data/debug.log

# 最後 100 行の JSON を確認
tail -100 data/debug.log | grep -E '(success|output|error|exit_code)' 
```

---

## 問題のチェックリスト

### ログが途切れているか確認

```bash
# 最後の行が空行か確認
tail -1 data/debug.log | od -c

# 最後の FULL_DETAIL が完全か確認
grep -A 10 FULL_DETAIL data/debug.log | tail -15
```

### 実際の出力長を確認

```bash
# ログファイルから "output" フィールドの長さを確認
grep -o '"output": "[^"]*"' data/debug.log | tail -1 | wc -c
```

---

## ログファイルをコピーして確認

```bash
# ログファイルをバックアップ
cp data/debug.log data/debug.log.full

# テキストエディタで開いて確認
vi data/debug.log
# または
cat data/debug.log | less
```

---

## もし出力が本当に途切れている場合

### 1. JSON の indent を確認

```bash
tail -200 data/debug.log | grep -B 5 -A 30 "success"
```

### 2. フィールドごとに確認

```bash
# success フィールド
grep '"success"' data/debug.log | tail -1

# exit_code フィールド
grep '"exit_code"' data/debug.log | tail -1

# output フィールド（長いので最初と最後を確認）
grep '"output"' data/debug.log | tail -1 | cut -c1-100
grep '"output"' data/debug.log | tail -1 | cut -c-100
```

### 3. ログファイル全体の統計

```bash
# セクションごとの行数
grep -c "\\[TOOL_RUNNER\\]" data/debug.log
grep -c "\\[VLLM_API\\]" data/debug.log
grep -c "\\[RESPONDER\\]" data/debug.log

# 成功/失敗の件数
grep -c '"success": true' data/debug.log
grep -c '"success": false' data/debug.log
```

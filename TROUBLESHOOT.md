# Troubleshooting

## git pull fails after running the bot

### 問題

実行後に `git pull` が失敗する：

```
error: Your local changes to the following files would be overwritten by merge:
  test/test_data/memory_integration.json
  test/test_data/runlog_integration.jsonl
Please commit your changes or stash them before you merge.

error: The following untracked working tree files would be overwritten by merge:
  data/runlog.jsonl
```

### 原因

- `./run.sh` 実行時に `data/runlog.jsonl` が生成される
- テスト実行時に `test/test_data/` 内のファイルが生成・変更される
- これらのファイルが git でトラッキングされていたため conflict が発生

### 解決方法

既に修正済みです。以下のコマンドで同期してください：

```bash
git pull
```

これで問題が解決します。

---

## ローカルで何か壊してしまった場合

### リセット

```bash
# 未コミット変更をすべて破棄
git reset --hard

# リモートの最新版と同期
git pull origin main
```

### 特定ファイルのみリセット

```bash
# test/test_data/ をリセット
git checkout -- test/test_data/

# data/ をリセット
git checkout -- data/
```

---

## 不要なファイルをクリーンアップ

```bash
# 未追跡ファイルをすべて削除
git clean -fd

# キャッシュをクリア
git gc
```

---

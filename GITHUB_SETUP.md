# GitHub リポジトリセットアップ手順

## 現在の状態

✅ ローカルgitリポジトリ初期化完了  
✅ 初回コミット完了  
⏳ GitHubリモートリポジトリ作成待ち

---

## 方法1: GitHub Web UIで作成（推奨）

### 1. GitHubでリポジトリ作成

1. https://github.com/new にアクセス
2. 以下の設定を入力：
   - **Repository name**: `vllm-bot`
   - **Description**: `Simple AI bot using vLLM v1/chat/completions with CLI and Telegram support`
   - **Visibility**: Public または Private
   - **Initialize this repository**: すべてチェックを外す（重要！）
3. "Create repository" をクリック

### 2. リモートを追加してプッシュ

```bash
cd ~/clawd/vllm-bot

# リモート追加（YOUR_USERNAMEを自分のGitHubユーザー名に置き換え）
git remote add origin https://github.com/YOUR_USERNAME/vllm-bot.git

# プッシュ
git push -u origin main
```

---

## 方法2: GitHub CLIで作成（gh未インストール）

GitHub CLIをインストールしてから実行：

```bash
# GitHub CLIインストール
sudo apt update
sudo apt install gh

# GitHub認証
gh auth login

# リポジトリ作成＆プッシュ
cd ~/clawd/vllm-bot
gh repo create vllm-bot --public --source=. --description="Simple AI bot using vLLM v1/chat/completions with CLI and Telegram support" --push
```

---

## 方法3: curlでAPI経由作成（上級者向け）

GitHubのPersonal Access Tokenを使用：

```bash
# Personal Access Token作成: https://github.com/settings/tokens
# Scopes: repo (full control of private repositories)

export GITHUB_TOKEN="your_token_here"
export GITHUB_USERNAME="your_username_here"

# リポジトリ作成
curl -H "Authorization: token $GITHUB_TOKEN" \
     -d '{"name":"vllm-bot","description":"Simple AI bot using vLLM v1/chat/completions with CLI and Telegram support","private":false}' \
     https://api.github.com/user/repos

# リモート追加＆プッシュ
cd ~/clawd/vllm-bot
git remote add origin https://github.com/$GITHUB_USERNAME/vllm-bot.git
git push -u origin main
```

---

## トラブルシューティング

### 既にリモートが存在する

```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/vllm-bot.git
```

### 認証エラー

HTTPS認証の場合、Personal Access Tokenを使用：

```bash
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/vllm-bot.git
```

または、SSH認証：

```bash
git remote set-url origin git@github.com:YOUR_USERNAME/vllm-bot.git
```

---

## 完了確認

プッシュ成功後、以下で確認：

```bash
git remote -v
git log --oneline
```

出力例：
```
origin  https://github.com/YOUR_USERNAME/vllm-bot.git (fetch)
origin  https://github.com/YOUR_USERNAME/vllm-bot.git (push)

ccdeca3 (HEAD -> main, origin/main) Initial commit: vLLM Bot with CLI and Telegram support
```

リポジトリURL: `https://github.com/YOUR_USERNAME/vllm-bot`

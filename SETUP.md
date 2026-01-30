# セットアップ

## 前提条件

- Python 3.8+
- vLLM サーバが http://localhost:8000/v1 で動作中

## インストール＆セットアップ

```bash
cd ~/vllm-bot
./setup.sh
```

自動で以下の処理を実行：
- Python 3 の確認
- 仮想環境（venv）の作成
- 依存パッケージのインストール
- ディレクトリ構造の作成（workspace/, data/）
- 設定ファイルの検証
- テストの実行

## 実行

```bash
./run.sh
```

対話型プロンプトが起動します。

## 設定変更

`config/config.json` を編集：

```json
{
  "vllm": {
    "base_url": "http://localhost:8000/v1",
    "model": "gpt-oss-medium"
  },
  "workspace": {
    "dir": "./workspace"
  }
}
```

編集後は `./run.sh` で起動します。

## テスト

```bash
venv/bin/python3 test/test_integration.py
```

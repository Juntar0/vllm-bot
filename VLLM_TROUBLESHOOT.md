# vLLM トラブルシューティング

## vLLM サーバ設定エラー

### 1. EngineCore encountered an issue (500 エラー)

```
[DEBUG VLLM_API] --- API Response ---
[DEBUG VLLM_API] ✗ Error Response:
[DEBUG VLLM_API]   Message: EngineCore encountered an issue. See stack trace (above) for the root cause.
[DEBUG VLLM_API]   Type: Internal Server Error
[DEBUG VLLM_API]   Code: 500
```

**原因**:
- vLLM サーバが内部エラーで停止
- モデルが正しく読み込まれていない
- GPU メモリ不足
- モデルが不適切な設定で起動

**解決方法**:

```bash
# vLLM サーバを停止
# (別ターミナルで実行している場合は Ctrl+C)

# vLLM サーバを再起動
python -m vllm.entrypoints.openai.api_server \
    --model gpt-oss-medium \
    --port 8000 \
    --tensor-parallel-size 1

# または config.json を確認
cat config/config.json | grep -A 5 vllm
```

### 2. JSON parsing error (Expecting property name...)

```
[DEBUG VLLM_API] ✗ Error: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)

[DEBUG PLANNER] --- JSON Parse Error ---
[DEBUG PLANNER] Error: Expecting property name...
[DEBUG PLANNER] Raw response: {'"error"...
```

**原因**:
- vLLM が JSON ではなく HTML や エラーページを返している
- API エンドポイントが間違っている
- vLLM サーバが起動していない

**解決方法**:

```bash
# 設定を確認
cat config/config.json | grep base_url

# テストして確認
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-medium",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }' | python -m json.tool
```

### 3. Connection refused (接続エラー)

```
[DEBUG VLLM_API] --- API Request Error ---
[DEBUG VLLM_API] ✗ Connection Error: HTTPConnectionPool(...): Failed to establish a new connection
```

**原因**:
- vLLM サーバが起動していない
- ポート番号が間違っている
- URL が正しくない

**解決方法**:

```bash
# vLLM サーバを起動
python -m vllm.entrypoints.openai.api_server \
    --model gpt-oss-medium \
    --port 8000

# 別ターミナルで確認
curl http://localhost:8000/v1/models | python -m json.tool
```

### 4. Empty response (Expecting value: line 1 column 1)

```
[DEBUG VLLM_API] --- API Response (Raw) ---
[DEBUG VLLM_API] Status Code: 200
[DEBUG VLLM_API] Content: (空)

[DEBUG VLLM_API] ✗ Error: Expecting value: line 1 column 1 (char 0)
```

**原因**:
- vLLM サーバが起動しているが、レスポンスが返されていない
- サーバが途中でクラッシュした
- タイムアウト

**解決方法**:

```bash
# vLLM サーバのログを確認
# (サーバ起動時のターミナルを確認)

# タイムアウトを増やす
# config.json で max_tokens を減らす
vi config/config.json
# "max_tokens": 512  # 2048 から減らす
```

---

## デバッグモードで詳細を確認

```bash
# Verbose debug mode を有効化
vi config/config.json

# 以下を設定
"debug": {
  "enabled": true,
  "level": "verbose"
}

./run.sh

# エラーが出たときに以下が表示されます:
# [DEBUG VLLM_API] --- API Request ---
# [DEBUG VLLM_API] --- API Response (Raw) ---
# [DEBUG PLANNER] --- JSON Parse Error ---
```

---

## vLLM サーバの起動テンプレート

### 基本

```bash
python -m vllm.entrypoints.openai.api_server \
    --model gpt-oss-medium \
    --port 8000
```

### GPU を指定

```bash
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
    --model gpt-oss-medium \
    --port 8000
```

### Tensor parallelism を使用

```bash
python -m vllm.entrypoints.openai.api_server \
    --model gpt-oss-medium \
    --port 8000 \
    --tensor-parallel-size 2
```

### メモリ不足の場合

```bash
python -m vllm.entrypoints.openai.api_server \
    --model gpt-oss-medium \
    --port 8000 \
    --gpu-memory-utilization 0.5  # 50% に制限
```

---

## API テスト

```bash
# モデルリスト確認
curl http://localhost:8000/v1/models | python -m json.tool

# 簡単な質問をテスト
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-medium",
    "messages": [
      {"role": "system", "content": "You are helpful."},
      {"role": "user", "content": "Hello, what is 1+1?"}
    ],
    "max_tokens": 50,
    "temperature": 0.0
  }' | python -m json.tool
```

---

## よくある設定ミス

| 問題 | 確認 |
|------|------|
| モデルが見つからない | `grep "model"` config.json を確認 |
| ポートが異なる | `grep "base_url"` config.json を確認 |
| vLLM が起動していない | `ps aux \| grep vllm` で確認 |
| GPU メモリ不足 | `nvidia-smi` で確認 |

---

## ログの保存と確認

```bash
# vLLM サーバのログを保存して実行
python -m vllm.entrypoints.openai.api_server \
    --model gpt-oss-medium \
    --port 8000 > vllm.log 2>&1 &

# ログを確認
tail -f vllm.log

# エラーだけ見る
grep ERROR vllm.log
grep error vllm.log
```
